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
- 模拟余额会统一保存在 [wallet_state.json](/Users/william/cobo/data/wallet_state.json)
- `.env` 里的 `DEMO_SIMULATED_BALANCE_ETH` 只负责提供初始余额
- 面向 Codex 的 `wallet_get_overview`、`wallet_prepare_transfer` 会直接返回余额来源说明
- 内部 CLI 的 `balance`、`estimate` 命令也保留了同类信息

## 当前已实现能力

当前对 Codex 暴露的 MCP 能力：

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

当前 MCP 暴露的是“只读 + 转账主流程”工具。

人工后台 Operator Console 负责的能力：

- 钱包私钥与 RPC 配置
- 模拟余额调整
- 白名单修改
- 地址簿修改
- 策略与权限开关修改

内部模块和 CLI 仍然保留更细的能力，但这些管理类写操作默认不再直接暴露给 Codex。

当前人工后台最小 Demo 页面结构：

- `Dashboard`
  - 看总览、最近提案、最近交易、最近人工资金调整
- `Wallet`
  - 改私钥和 RPC
- `Balance Lab`
  - 做模拟入金、出金、直接设余额
- `Whitelist`
  - 管理白名单地址
- `Address Book`
  - 管理联系人、别名、备注
- `Policy`
  - 改写入开关、执行模式、白名单开关、本地授权开关、限额和 PIN

## 为什么要合并

原先拆得更细的流程里，有几类明显可以合并：

- 账户信息 + 余额 + 策略
  - 都属于“启动前看一下当前钱包状态”
  - 现在合并成 `wallet_get_overview`
- 预估转账 + 创建提案
  - 实际上创建提案时本来就会做预估
  - 现在合并成 `wallet_prepare_transfer`
- 授权检查 + 最终执行
  - 对 Codex 来说它们都属于“确认后往下执行”
  - 现在由 `wallet_execute_transfer` 对外统一包装
  - 默认模式会直接执行
  - 严格模式会先返回本地 PIN 授权指引

我保留成独立工具的只有这些：

- `wallet_list_recipients`
  - 因为联系人列表本身就是独立查询动作
- `wallet_get_receive_card`
  - 因为“别人怎么给我转账”也是独立场景
  - 它只负责展示当前钱包的收款信息，不涉及任何写操作
- `wallet_get_proposal / wallet_cancel_proposal`
  - 因为提案经常需要单独回看状态、或在执行前主动取消
- `wallet_confirm_proposal`
  - 因为这是“用户已确认”的关键安全边界
- `wallet_get_transaction_status`
  - 因为执行后查状态仍然是独立动作
- `wallet_list_transactions`
  - 因为“最近发过哪些交易/取消过哪些提案”本身就是独立查询动作
- `wallet_list_proposals`
  - 因为它解决的是另一件事：查看哪些提案还在处理中、下一步该做什么
  - 默认会优先展示未完成提案，而不是只看历史结果

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

如果你不想手改 JSON，现在建议通过人工后台 Operator Console 或 CLI 管理地址簿。

现在创建提案或预估时，工具返回里会额外包含：

- `recipient_preview`
- `confirmation_preview`

这两个字段就是专门给 Codex 做“确认前回显”用的。Codex 应先把里面的联系人名称、实际地址、金额和手续费展示给你，再继续确认执行。

另外，当前版本在 `wallet_prepare_transfer` 阶段就会检查余额是否足够支付：

- 转账金额
- 预估手续费

如果总成本大于当前余额，提案会直接被拒绝，不会先创建再到后面失败。

## 白名单

当前白名单是一个可选的权限边界，和地址簿不是一回事：

- 地址簿：解决“`burn` / `小红` 这种名字对应哪个地址”
- 白名单：解决“这个地址是否允许被转账”

当 `DEMO_REQUIRE_WHITELIST=true` 时：

- 只有白名单中的地址，才允许创建提案
- 已创建但尚未执行的提案，如果目标地址后来被移出白名单，也会被阻止继续确认或执行
- 这种阻止不会产生新状态，而是让提案显示 `ready_for_execution=false`

当前对 Codex 只保留白名单只读查看：

- `wallet_list_whitelist`

白名单的新增、删除和备注修改现在统一走人工后台 Operator Console 或 CLI，不再直接交给 Codex。

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

## 提案状态速览

如果你只想先理解“提案现在走到哪一步了”，记这几个状态就够了：

- `pending`
  - 提案刚创建出来
  - 说明金额、地址、手续费已经生成
  - 但你还没明确回复“确认”或“取消”
- `confirmed_by_user`
  - 只会在默认模式常见
  - 表示你已经确认
  - 下一步可以直接执行
- `awaiting_local_authorization`
  - 只会在严格模式出现
  - 表示你已经确认，但本地 PIN 还没输入
  - 这时还不能执行
- `authorized`
  - 只会在严格模式出现
  - 表示本地 PIN 已通过
  - 下一步才允许执行
- `executed`
  - 已执行完成
- `rejected`
  - 已取消
- `expired`
  - 已过期

默认模式最常见的路径是：

```text
pending -> confirmed_by_user -> executed
```

严格模式最常见的路径是：

```text
pending -> awaiting_local_authorization -> authorized -> executed
```

如果你想看完整状态流转图和每个状态的触发条件，可以看 [docs/architecture.md](docs/architecture.md)。

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
DEMO_REQUIRE_WHITELIST=false
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

如果你要测试白名单，再额外改成：

```env
DEMO_REQUIRE_WHITELIST=true
```

如果你要使用人工控制台，再额外建议配置：

```env
DEMO_OPERATOR_PIN=135790
```

补充说明：

- `DEMO_SIMULATED_BALANCE_ETH` 不是每次请求都直接读取的实时余额
- 它只用于初始化本地模拟钱包状态
- 之后余额会和钱包元信息一起保存在 [wallet_state.json](/Users/william/cobo/data/wallet_state.json)
- `DEMO_OPERATOR_PIN` 用来登录人工控制台
- 如果不配置 `DEMO_OPERATOR_PIN`，当前 Demo 会回退使用 `DEMO_APPROVAL_PIN`

## 启动人工控制台

```bash
uv run cobo-wallet-operator
```

人工控制台当前提供 6 个页面：

- `Dashboard`
- `Wallet`
- `Balance Lab`
- `Whitelist`
- `Address Book`
- `Policy`

适合通过人工控制台完成的动作：

- 修改私钥或 RPC
- 调整模拟余额
- 管理白名单
- 管理地址簿
- 修改写入开关、白名单开关和本地授权开关

## 内部 CLI / 调试命令

这些命令主要用于本地调试、回归测试和人工兜底管理。

- Codex 默认不会直接调用它们
- 地址簿和白名单这类敏感写操作，建议优先走 Operator Console
- CLI 仍然保留，是为了方便你在本地脚本化处理或排障

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

查看收款信息：

```bash
uv run cobo-wallet-demo receive-card
```

查看白名单：

```bash
uv run cobo-wallet-demo list-whitelist
```

把联系人或地址加入白名单：

```bash
uv run cobo-wallet-demo allow-recipient --target burn
```

把联系人或地址移出白名单：

```bash
uv run cobo-wallet-demo revoke-recipient --target burn
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

只查看待处理提案：

```bash
uv run cobo-wallet-demo list-proposals --status pending --status confirmed_by_user --status awaiting_local_authorization --status authorized
```

## 启动 MCP Server

```bash
uv run cobo-wallet-mcp
```

## 在 Codex 里注册

```bash
codex mcp add cobo-wallet --env DEMO_WRITE_ENABLED=true --env DEMO_EXECUTION_MODE=simulate --env DEMO_REQUIRE_LOCAL_AUTH=false --env DEMO_REQUIRE_WHITELIST=false -- uv run --project /Users/william/cobo cobo-wallet-mcp
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

如果你想让 Codex 直接展示收款信息，可以说：

```text
显示我的收款信息
```

或者：

```text
把我的收款地址发给我
```

或者：

```text
生成一段可以转发给别人的收款文本
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

如果你要维护联系人、白名单、私钥或测试余额，请改用人工控制台，而不是让 Codex 直接修改。

## 当前边界

- 当前真正可用的是本地模拟执行
- `sepolia` 真实广播接口还没有接通
- 私钥始终只保留在本地 `.env`
- 如果你关闭本地二次授权，流程会更方便，但安全边界也会更弱

## 文档

更完整的架构说明见 [docs/architecture.md](/Users/william/cobo/docs/architecture.md)。
