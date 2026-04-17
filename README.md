# COBO Wallet MCP

一个用 Python 实现的本地 MCP Server，用来让 Codex 以工具调用的方式访问一个受控的加密货币钱包。

当前默认流程已经恢复成更简化的模式：

- Codex 创建提案
- Codex 展示金额、收款地址、手续费
- 你在对话里回复“确认”
- Codex 先调用 `wallet_confirm_proposal`
- 只有这一步成功后，Codex 才能调用 `wallet_execute_transfer`

如果你之后想切回更严格的模式，也保留了开关：

- 把 `DEMO_REQUIRE_LOCAL_AUTH=true`
- 然后就会恢复成“对话确认 + 本地终端 PIN”双重确认

当前默认仍然推荐 `simulate` 模式：

- 会完整跑通提案和确认流程
- 但不会真的把交易广播到链上
- 当前 `.env` 已把本地模拟余额默认设成 `50 ETH`，方便直接测试

## 当前已实现能力

- `wallet_get_overview`
- `wallet_list_recipients`
- `wallet_add_recipient`
- `wallet_update_recipient`
- `wallet_delete_recipient`
- `wallet_prepare_transfer`
- `wallet_get_proposal`
- `wallet_cancel_proposal`
- `wallet_confirm_proposal`
- `wallet_execute_transfer`
- `wallet_get_transaction_status`
- `wallet_list_transactions`

当前 MCP 暴露的是“高层工具”，内部仍然保留了更细的模块，但默认不再直接暴露给 Codex。

## 为什么要合并

原先的 MCP 工具里，有几类明显可以合并：

- `get_account + get_balance + list_policy`
  - 都属于“启动前看一下当前钱包状态”
  - 现在合并成 `wallet_get_overview`
- `estimate_transfer + create_transfer_proposal`
  - 实际上创建提案时本来就会做预估
  - 现在合并成 `wallet_prepare_transfer`
- `request_local_authorization + confirm_transfer`
  - 对 Codex 来说它们都属于“确认后往下执行”
  - 现在合并成 `wallet_execute_transfer`
  - 默认模式会直接执行
  - 严格模式会先返回本地 PIN 授权指引

我保留成独立工具的只有这些：

- `wallet_list_recipients`
  - 因为联系人列表本身就是独立查询动作
- `wallet_add_recipient / wallet_update_recipient / wallet_delete_recipient`
  - 因为地址簿维护不是转账主流程，但又是高频的独立管理动作
- `wallet_get_proposal / wallet_cancel_proposal`
  - 因为提案经常需要单独回看状态、或在执行前主动取消
- `wallet_confirm_proposal`
  - 因为这是“用户已确认”的关键安全边界
- `wallet_get_transaction_status`
  - 因为执行后查状态仍然是独立动作
- `wallet_list_transactions`
  - 因为“最近发过哪些交易/取消过哪些提案”本身就是独立查询动作

## 地址命名化

现在 `to` 参数支持两种写法：

- 直接写完整地址
- 直接写联系人名称或别名

当前内置了一个示例联系人：

- `burn`
- 别名：`dead`、`销毁地址`、`黑洞地址`

你可以直接对 Codex 说：

```text
帮我向 burn 转 0.01 ETH
```

或者：

```text
帮我向 销毁地址 转 0.01 ETH
```

本地地址簿文件在 [address_book.json](/Users/william/cobo/data/address_book.json)，你之后只要往里面继续加联系人就可以。

如果你不想手改 JSON，现在也可以直接通过 MCP 或 CLI 管理地址簿：

- 新增：`wallet_add_recipient`
- 更新：`wallet_update_recipient`
- 删除：`wallet_delete_recipient`

现在创建提案或预估时，工具返回里会额外包含：

- `recipient_preview`
- `confirmation_preview`

这两个字段就是专门给 Codex 做“确认前回显”用的。Codex 应先把里面的联系人名称、实际地址、金额和手续费展示给你，再继续确认执行。

另外，当前版本在 `wallet_prepare_transfer` 阶段就会检查余额是否足够支付：

- 转账金额
- 预估手续费

如果总成本大于当前余额，提案会直接被拒绝，不会先创建再到后面失败。

## 默认交互流程

```text
用户说要转账
-> Codex 调用 wallet_prepare_transfer
-> Codex 展示 金额 / 地址 / 手续费
-> 用户回复“确认”
-> Codex 调用 wallet_confirm_proposal
-> Codex 调用 wallet_execute_transfer
-> MCP 执行模拟转账
```

## 可选严格模式

如果把 `DEMO_REQUIRE_LOCAL_AUTH=true`，流程会变成：

```text
用户说要转账
-> Codex 调用 wallet_prepare_transfer
-> Codex 展示 金额 / 地址 / 手续费
-> 用户回复“确认”
-> Codex 调用 wallet_confirm_proposal
-> Codex 调用 wallet_execute_transfer
-> 本地终端输入 PIN
-> Codex 再调用 wallet_execute_transfer
```

## 安装

```bash
uv sync
```

## 配置

先复制示例配置：

```bash
cp .env.example .env
```

开发阶段建议保持：

```env
DEMO_WRITE_ENABLED=false
DEMO_EXECUTION_MODE=simulate
DEMO_SIMULATED_BALANCE_ETH=50
DEMO_REQUIRE_LOCAL_AUTH=false
```

如果你要测试实际“确认执行”步骤，再临时改成：

```env
DEMO_WRITE_ENABLED=true
DEMO_EXECUTION_MODE=simulate
```

如果你要开启严格模式，再额外改成：

```env
DEMO_REQUIRE_LOCAL_AUTH=true
```

## 本地 CLI 演示

查看账户：

```bash
uv run cobo-wallet-demo account
```

查看余额：

```bash
uv run cobo-wallet-demo balance
```

查看策略：

```bash
uv run cobo-wallet-demo policy
```

查看地址簿联系人：

```bash
uv run cobo-wallet-demo recipients
```

新增联系人：

```bash
uv run cobo-wallet-demo add-recipient --name 小红 --address 0x000000000000000000000000000000000000dEaD --alias xh --alias red --note 测试联系人
```

更新联系人：

```bash
uv run cobo-wallet-demo update-recipient --name-or-alias 小红 --alias xh --alias hong --note 新备注
```

删除联系人：

```bash
uv run cobo-wallet-demo delete-recipient --name-or-alias 小红
```

预估转账：

```bash
uv run cobo-wallet-demo estimate --to 0x000000000000000000000000000000000000dEaD --amount 0.01
```

创建提案：

```bash
uv run cobo-wallet-demo propose --to 0x000000000000000000000000000000000000dEaD --amount 0.01
```

查看提案详情：

```bash
uv run cobo-wallet-demo get-proposal --proposal-id proposal_xxxxxxxx
```

取消提案：

```bash
uv run cobo-wallet-demo cancel-proposal --proposal-id proposal_xxxxxxxx
```

记录“用户已确认”：

```bash
uv run cobo-wallet-demo confirm-proposal --proposal-id proposal_xxxxxxxx
```

默认模式下执行已确认提案：

```bash
DEMO_WRITE_ENABLED=true DEMO_EXECUTION_MODE=simulate uv run cobo-wallet-demo confirm --proposal-id proposal_xxxxxxxx
```

如果你开启了严格模式，再使用：

```bash
env DEMO_REQUIRE_LOCAL_AUTH=true uv run cobo-wallet-demo confirm-proposal --proposal-id proposal_xxxxxxxx
uv run cobo-wallet-authorize --proposal-id proposal_xxxxxxxx
env DEMO_REQUIRE_LOCAL_AUTH=true DEMO_WRITE_ENABLED=true DEMO_EXECUTION_MODE=simulate uv run cobo-wallet-demo confirm --proposal-id proposal_xxxxxxxx
```

查询交易状态：

```bash
uv run cobo-wallet-demo tx-status --tx-hash sim_xxxxxxxx
```

查看交易历史：

```bash
uv run cobo-wallet-demo list-transactions --limit 10
```

查看提案列表：

```bash
uv run cobo-wallet-demo list-proposals
```

## 启动 MCP Server

```bash
uv run cobo-wallet-mcp
```

## 在 Codex 里注册

```bash
codex mcp add cobo-wallet --env DEMO_WRITE_ENABLED=true --env DEMO_EXECUTION_MODE=simulate --env DEMO_REQUIRE_LOCAL_AUTH=false -- uv run --project /Users/william/cobo cobo-wallet-mcp
```

查看是否注册成功：

```bash
codex mcp get cobo-wallet
```

## 推荐的 Codex 使用方式

你可以直接对 Codex 说：

```text
帮我转 0.05 ETH 到 0x000000000000000000000000000000000000dEaD
```

默认模式下，理想交互应该是：

1. Codex 调用 `wallet_prepare_transfer`
2. Codex 把 `proposal_id`、`联系人名称`、`实际地址`、`金额`、`手续费` 展示给你
3. 你回复“确认”
4. Codex 调用 `wallet_confirm_proposal`
5. Codex 调用 `wallet_execute_transfer`

如果你中途想撤销，也可以直接对 Codex 说：

```text
取消 proposal_xxxxxxxx
```

如果你想回看历史，也可以直接对 Codex 说：

```text
帮我查看最近 10 条转账历史
```

现在这里的“历史”会同时包含：

- 已执行的转账
- 已取消的转账提案

如果你先要维护联系人，也可以直接对 Codex 说：

```text
把 0x000000000000000000000000000000000000dEaD 保存成联系人 burn2，别名为 dead2
```

## 当前边界

- 当前真正可用的是本地模拟执行
- `sepolia` 真实广播接口还没有接通
- 私钥始终只保留在本地 `.env`
- 如果你关闭本地二次授权，流程会更方便，但安全边界也会更弱

## 文档

更完整的架构说明见 [docs/architecture.md](/Users/william/cobo/docs/architecture.md)。
