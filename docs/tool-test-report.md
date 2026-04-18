# COBO Wallet MCP 工具测试报告

测试日期：2026-04-18

## 结论

- 综合结果：通过
- 集成检查：46 / 46 通过
- 运行级检查：2 / 2 通过
- 本轮确认的重点：
  - Agent 转账主流程可正常完成
  - Operator Console 的配置修改可以即时同步到 MCP 侧，无需重启
  - 敏感写操作边界已收紧，越权请求会被门卫工具直接拒绝
  - Intent Integrity 与金额一致性校验已在执行前生效

## 测试环境

- 集成测试方式：使用临时 `.env` 与临时 `DEMO_DATA_DIR`
- 数据隔离：不污染当前项目正式 `.env` 与 [data](/Users/william/cobo/data)
- 执行模式：`simulate`
- 链配置：`chain_id = 11155111 (Ethereum Sepolia)`
- 初始模拟余额：`50 ETH`
- 本轮集成测试中 `SEPOLIA_RPC_URL` 置空，重点验证本地状态机、权限边界、热更新与风控逻辑
- 因未连接 RPC，本轮集成测试中的手续费估算为 `0 ETH`，这不影响提案、确认、执行、历史记录和安全校验验证

## 覆盖范围

### 1. MCP 核心工具

本轮实际验证了以下 13 个面向 Codex 的 MCP 工具：

- `wallet_get_overview`
- `wallet_check_request_capability`
- `wallet_list_recipients`
- `wallet_list_whitelist`
- `wallet_get_receive_card`
- `wallet_prepare_transfer`
- `wallet_get_proposal`
- `wallet_confirm_proposal`
- `wallet_execute_transfer`
- `wallet_cancel_proposal`
- `wallet_get_transaction_status`
- `wallet_list_transactions`
- `wallet_list_proposals`

### 2. Operator Console / 后台服务能力

本轮实际验证了以下后台管理动作：

- `verify_operator_pin`
- `update_wallet_config`
- `update_policy_config`
- `deposit_balance`
- `withdraw_balance`
- `set_balance`
- `add_address_book_entry`
- `add_whitelist_entry`
- `get_dashboard`

### 3. 运行级检查

- `uv run python -m compileall src scripts`
- `uv run cobo-wallet-operator`

## 实测结果

### 1. 转账主流程

已实际走通以下完整链路：

- `wallet_prepare_transfer -> wallet_confirm_proposal -> wallet_execute_transfer -> wallet_get_transaction_status`

验证结果：

- 能成功创建提案
- 用户确认后，提案状态会进入 `confirmed_by_user`
- 执行后会生成模拟交易哈希
- `wallet_get_transaction_status` 能查回 `confirmed`
- `wallet_list_transactions` 能看到已执行记录

另外也验证了重复请求场景：

- 对同一联系人、同一金额连续发起两次转账请求，会生成两个不同的 `proposal_id`
- 不会因为“收款人相同 + 金额相同”而错误复用旧提案

### 2. 取消流程与历史记录

已实际验证：

- `wallet_cancel_proposal` 可取消未执行提案
- `wallet_list_transactions` 会同时展示：
  - `executed`
  - `cancelled`
- `wallet_list_proposals` 会保留并展示：
  - `executed`
  - `rejected`

这说明“提案列表”和“交易历史”都已经能正确反映取消行为。

### 3. Web / 配置热更新是否即时

本轮重点验证了 Operator Console 修改配置后，MCP 侧是否无需重启即可读取新状态。

已确认以下改动会即时生效：

- `write_enabled`
  - 先将已确认提案置于可执行状态
  - 再通过后台把 `write_enabled` 改为 `false`
  - `wallet_execute_transfer` 会立即报“只读模式”
  - 再改回 `true` 后，同一提案可直接继续执行

- `require_whitelist`
  - 打开白名单开关后，`burn` 会立即被拦截
  - 加入白名单后，无需重启即可再次成功发起提案

- `max_transfer_eth`
  - 将单笔限额从 `0.05` 改为 `0.005`
  - 立即拦截 `0.01 ETH`
  - 再改回 `0.05` 后，无需重启即可再次发起

- 地址簿
  - 后台新增 `Zoey`
  - `wallet_list_recipients` 立即可见
  - 后续可以直接用名字 `Zoey` 发起转账

- 白名单
  - 后台新增白名单地址后
  - `wallet_list_whitelist` 立即可见

- 余额
  - 后台执行 `deposit / withdraw / set_balance`
  - `wallet_get_overview` 会立即返回最新余额

结论：

- 当前项目已经实现“后台改配置，MCP 下一次调用立即读取新值”的热更新行为
- 这一点主要通过 `build_context(reload_env=True)` 的运行时刷新生效

### 4. 权限边界与安全问题

#### `wallet_check_request_capability`

本轮已验证它会直接拦截以下越权请求：

- 修改余额
- 修改白名单
- 修改私钥
- 修改地址簿
- 修改策略 / 限额

同时，它仍然允许以下正常请求继续流转：

- 发起转账
- 查询余额 / 地址 / 总览

这说明当前“门卫工具”的边界是合理的：允许 Agent 继续完成转账主流程，但不允许 Agent 改动敏感后台配置。

#### 余额前置校验

本轮已验证：

- 当余额只有 `0.001 ETH` 时，发起 `0.01 ETH` 转账会在 `wallet_prepare_transfer` 阶段直接失败
- 失败后不会创建任何新提案

这说明“余额不足”问题已经从执行阶段前移到了提案创建阶段。

#### 白名单运行时拦截

本轮已验证：

- 白名单开启后，非白名单地址无法创建提案
- 白名单更新后，无需重启即可恢复允许

#### Intent Integrity

本轮已做两类篡改测试：

1. 篡改收款地址
   - 在提案确认后，直接修改底层 `proposals.json` 中的 `to`
   - 执行时被 `intent_hash` 校验拒绝
   - 审计日志写入 `wallet_intent_integrity_failed`

2. 篡改金额显示字段
   - 在提案确认后，只修改 `amount_eth`
   - 保持 `amount_wei` 不变
   - 执行时被“金额一致性校验”拒绝
   - 提案不会被错误标记为已执行

结论：

- 当前已经不是“只存一个 intent_hash 但执行前不校验”的状态
- 执行前确实会校验：
  - 核心交易意图是否被篡改
  - `amount_eth` 与 `amount_wei` 是否一致

## 运行级检查

### 1. 代码编译检查

命令：

```bash
uv run python -m compileall src scripts
```

结果：通过

### 2. Operator Console 启动冒烟

命令：

```bash
uv run cobo-wallet-operator
```

结果：
- Streamlit 成功启动
- 本次启动分配到本地地址：`http://localhost:8503`
- 使用 `curl -I http://127.0.0.1:8503` 返回 `HTTP/1.1 200 OK`

说明：这证明 Web 管理台不仅能启动进程，而且已实际对外响应 HTTP 请求
