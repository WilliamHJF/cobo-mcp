# COBO Wallet MCP 工具测试报告

测试日期：2026-04-18

## 结论

- 结果：通过
- 覆盖范围：24 个能力项
- 通过数量：24
- 失败数量：0
- 测试方式：使用临时数据目录执行，不污染当前正式数据

本次测试覆盖了：

- 当前对 Codex 暴露的 MCP 高层工具
- 仓库中仍保留的内部工具模块
- 严格模式下的本地授权 CLI：`cobo-wallet-authorize`

## 测试环境

- 执行模式：`simulate`
- 默认流程模式：`DEMO_REQUIRE_LOCAL_AUTH=false`
- 严格流程模式：`DEMO_REQUIRE_LOCAL_AUTH=true`
- 白名单模式：`DEMO_REQUIRE_WHITELIST=true`
- 模拟余额：`50 ETH`
- 数据目录：临时目录，不使用 [data](/Users/william/cobo/data)

## 覆盖范围

### 1. 默认模式主流程

- `get_overview`
- `get_account`
- `get_balance`
- `list_policy`
- `list_recipients`
- `list_whitelist`
- `get_receive_card`
- `estimate_transfer`
- `add_recipient`
- `update_recipient`
- `allow_recipient`
- `revoke_recipient`
- `create_transfer_proposal`
- `get_proposal`
- `list_proposals`
- `confirm_proposal`
- `execute_transfer`
- `get_transaction_status`
- `list_transactions`
- `cancel_proposal`
- `request_local_authorization`
- `delete_recipient`

验证结果：

- 联系人增删改查正常
- 白名单增删查正常
- `allow_recipient` 默认只写地址，不再自动写入联系人名称
- 转账提案可正常创建、确认、执行
- 已执行交易可在交易状态与历史记录中查到
- 已取消提案可在提案列表中过滤出来
- 在关闭本地授权时，`request_local_authorization` 会正确返回“无需本地授权”的提示

### 2. 严格模式 + 白名单流程

- `get_overview`
- `list_policy`
- `create_transfer_proposal`
- `allow_recipient`
- `list_whitelist`
- `confirm_proposal`
- `request_local_authorization`
- `confirm_transfer`
- `execute_transfer`
- `cobo-wallet-authorize`

验证结果：

- 白名单开启且目标未放行时，创建提案会被正确阻止
- 放行目标地址后，可正常创建提案
- `confirm_proposal` 会把提案推进到 `awaiting_local_authorization`
- `request_local_authorization` 会返回正确的本地授权引导
- `cobo-wallet-authorize` 可正常完成一次性本地授权
- 授权后，`confirm_transfer` 与 `execute_transfer` 都可成功完成模拟转账

## 按工具汇总

| 工具/命令 | 结果 | 备注 |
| --- | --- | --- |
| `get_overview` | 通过 | 默认模式与严格模式都验证 |
| `get_account` | 通过 | 返回钱包配置状态正常 |
| `get_balance` | 通过 | 模拟余额读取正常 |
| `list_policy` | 通过 | 默认模式与严格模式都验证 |
| `list_recipients` | 通过 | 初始列表与更新后列表都验证 |
| `list_whitelist` | 通过 | 默认模式与严格模式都验证 |
| `get_receive_card` | 通过 | 可生成 Codex 展示用收款信息 |
| `estimate_transfer` | 通过 | 可返回手续费与余额校验结果 |
| `add_recipient` | 通过 | 新增联系人成功 |
| `update_recipient` | 通过 | 更新联系人成功 |
| `delete_recipient` | 通过 | 删除联系人成功 |
| `allow_recipient` | 通过 | 默认仅写地址；显式传 `name` 时可写展示名 |
| `revoke_recipient` | 通过 | 可按地址移出白名单 |
| `create_transfer_proposal` | 通过 | 默认模式、白名单阻止场景、严格模式都验证 |
| `get_proposal` | 通过 | 可查看待确认提案 |
| `list_proposals` | 通过 | 可查看全部提案并按状态过滤 |
| `confirm_proposal` | 通过 | 默认模式与严格模式都验证 |
| `request_local_authorization` | 通过 | 开关开启/关闭两种场景都验证 |
| `confirm_transfer` | 通过 | 严格模式授权后执行成功 |
| `execute_transfer` | 通过 | 默认模式直接执行；严格模式前后两阶段都验证 |
| `get_transaction_status` | 通过 | 可查询模拟交易状态 |
| `list_transactions` | 通过 | 可返回已执行与已取消记录 |
| `cancel_proposal` | 通过 | 可取消待执行提案 |
| `cobo-wallet-authorize` | 通过 | 本地授权 CLI 正常 |

## 当前剩余风险

- 本次测试只覆盖 `simulate` 模式，没有覆盖真实链上广播
- 当前项目的 `sepolia` 真实广播路径仍未接入完整签名与发送实现
- 因此，本报告可以证明本地模拟流程和工具编排正常，但不能证明真实链上转账已经可用

## 结论建议

- 当前项目的本地模拟钱包流程已经达到“可演示、可交互、可回归测试”的状态
- 如果下一步要继续提高可信度，优先建议补：
- `sepolia` 真实广播实现
- 一条自动化测试脚本，把本次手工回归流程固化成可重复执行的命令
