# COBO Wallet MCP 工具测试报告

测试日期：2026-04-18

## 结论

- 结果：通过
- 总检查项：20
- 通过数量：20
- 失败数量：0
- 测试方式：使用临时 `.env` 和临时数据目录执行，不污染当前正式数据

本次验证覆盖三部分：

- 当前对 Codex 暴露的 12 个 MCP 高层工具
- Operator Console 背后的 6 个关键管理动作
- 2 个运行级检查：`compileall` 与 Streamlit 启动冒烟

## 测试环境

- 执行模式：`simulate`
- 写入开关：`DEMO_WRITE_ENABLED=true`
- 本地授权：`DEMO_REQUIRE_LOCAL_AUTH=false`
- 白名单开关：`DEMO_REQUIRE_WHITELIST=false`
- 初始模拟余额：`50 ETH`
- 人工额外入金：`1.5 ETH`
- 数据目录：临时目录，不使用 [data](/Users/william/cobo/data)

## 已验证项目

### 1. MCP 高层工具

以下 12 个工具都已在隔离环境中实际调用：

- `wallet_get_overview`
- `wallet_list_recipients`
- `wallet_list_whitelist`
- `wallet_get_receive_card`
- `wallet_prepare_transfer`
- `wallet_get_proposal`
- `wallet_cancel_proposal`
- `wallet_confirm_proposal`
- `wallet_execute_transfer`
- `wallet_get_transaction_status`
- `wallet_list_transactions`
- `wallet_list_proposals`

验证结果：

- 可读取当前钱包总览、联系人、白名单和收款信息
- 可创建提案并返回确认卡片
- 可查询单条提案详情
- 可完成“确认后执行”的本地模拟转账
- 可查询模拟交易状态
- 可把已取消提案一并展示在交易历史中

### 2. Operator Console 关键能力

以下 6 个后台管理动作已在隔离环境中实际验证：

- `verify_operator_pin`
- `update_wallet_config`
- `deposit_balance`
- `add_address_book_entry`
- `add_whitelist_entry`
- `get_dashboard`

验证结果：

- 管理员 PIN 校验正常
- 可写入新的私钥配置，并正确派生地址
- 可人工增加模拟余额，并写入资金调整记录
- 可新增联系人
- 可新增白名单地址
- 仪表盘可正确汇总余额、提案和交易信息

### 3. 运行级检查

- `uv run python -m compileall src scripts`
  - 通过
- `uv run cobo-wallet-operator`
  - 通过
  - Streamlit 成功启动，输出本地访问地址 `http://localhost:8501`

## 关键回归结果

本次隔离测试中，实际走通了两条关键路径：

1. 执行路径
   - Operator Console 写入私钥
   - 人工入金后余额变为 `51.5 ETH`
   - `wallet_prepare_transfer -> wallet_confirm_proposal -> wallet_execute_transfer`
   - 成功生成模拟交易哈希
   - `wallet_get_transaction_status` 可正确查回状态

2. 取消路径
   - 再创建第二条提案
   - 调用 `wallet_cancel_proposal`
   - `wallet_list_transactions` 中可同时看到：
   - 一条 `executed`
   - 一条 `cancelled`

## 当前剩余风险

- 本次只验证了 `simulate` 模式，没有验证真实链上广播
- `DEMO_EXECUTION_MODE=sepolia` 仍未接入完整签名与发送实现
- Operator Console 目前是 Demo 级本地管理台，不具备生产级鉴权与审计隔离

## 结论建议

- 当前项目已经达到“本地可用的最小 Demo”状态
- 适合继续拿来演示 Codex 调 MCP 钱包、人工后台管敏感配置的完整分层
- 如果下一步要继续提高可信度，优先建议补：
- `sepolia` 真实广播实现
- Operator Console 的自动化测试
- 更明确的生产级权限模型
