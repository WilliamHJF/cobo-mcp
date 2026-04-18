# Cryptocurrency Wallet MCP

Link：https://github.com/WilliamHJF/cobo-mcp

一个用 Python 实现的本地 MCP 钱包 Demo。

这个项目的目标是做一个适合本地演示的 AI Agent 钱包原型：

- AI Agent 可以查询钱包信息、创建转账提案、确认提案、执行转账、查看历史
- 敏感配置不交给 Agent 直接修改，而是交给人工后台 `Operator Console`
- 默认使用 `simulate` 模式，本地完整跑通转账流程，但不会真正广播到链上
- 适合本地接入 Codex 等支持 MCP 的 AI Agent 进行演示

## 1. 项目现在能做什么

当前项目已经实现：

- 钱包总览查询
- 钱包收款信息展示
- 地址簿联系人解析
- 白名单校验
- 转账提案创建
- 对话确认后执行转账
- 提案取消
- 交易历史查询
- Operator Console 人工管理台

重要说明：

- 当前可稳定使用的执行模式是 `simulate`
- `simulate` 模式会真正更新本地余额、提案、交易历史
- 但不会向 Sepolia 或主网广播任何真实交易

## 2. 你需要准备什么

开始前，请先准备：

- `Git`
- `Python 3.11` 或更高版本
- `uv`

这个项目推荐全程使用 `uv`。

如果你还没有安装 `uv`，常见安装方式是：

```bash
pip install uv
```

安装完成后可以检查：

```bash
uv --version
python --version
```

## 3. 从 GitHub 下载到本地

先把项目 clone 到本地：

```bash
git clone https://github.com/WilliamHJF/cobo-mcp.git
cd cobo-mcp
```

然后安装依赖：

```bash
uv sync
```

如果你想确认环境已经装好，可以先跑一次：

```bash
uv run python -m compileall src scripts
```

## 4. 最重要的一步：先配置 `.env`

GitHub 上不会包含 `.env`，因为这个文件不会提交到仓库。

clone 完项目后，请先在项目根目录创建 `.env`：

```bash
cp .env.example .env
```

如果你不想先打开 `.env.example`，也可以直接新建 `.env`，然后粘贴下面这份当前示例配置：

```dotenv
# =========================
# COBO Wallet MCP 本地配置
# =========================
#
# 当前示例测试钱包地址：
# 0xC18f9e83970032AEC511123F311A10b0A2c68256
#
# 安全提醒：
# - 只用于 Sepolia 测试链和本地 Demo
# - 不要复用到主网
# - 如果你要公开 fork 或分享仓库，请先替换 DEMO_PRIVATE_KEY 和 PIN
# - 当前没有单独设置 DEMO_OPERATOR_PIN，Operator Console 会回退使用 DEMO_APPROVAL_PIN

SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
DEMO_PRIVATE_KEY=0xc5090130562cc12fbaaaedd107d9738ea65a1346d2c80cf34e46a3c8b8a58125
DEMO_WRITE_ENABLED=true
DEMO_EXECUTION_MODE=simulate
DEMO_SIMULATED_BALANCE_ETH=50
DEMO_REQUIRE_WHITELIST=true
DEMO_REQUIRE_LOCAL_AUTH=false
DEMO_APPROVAL_PIN=123456
DEMO_CHAIN_ID=11155111
DEMO_MAX_TRANSFER_ETH=0.5
DEMO_PROPOSAL_TTL_MINUTES=30
DEMO_LOCAL_AUTH_TTL_MINUTES=5
DEMO_DATA_DIR=./data
```

注意：

- 这份配置和当前项目演示环境一致，复制后就能直接跑通 README 里的流程
- 当前模板把 `DEMO_WRITE_ENABLED` 设成了 `true`，是为了让演示流程可以直接执行；如果你只想先做只读测试，可以改回 `false`
- 当前模板没有设置 `DEMO_OPERATOR_PIN`，所以 Operator Console 登录时会回退使用 `DEMO_APPROVAL_PIN=123456`

## 5. 每个关键变量是什么意思

下面是新手最需要理解的几个变量。

### 与启动最相关的变量

| 变量名 | 是否建议配置 | 作用 |
| --- | --- | --- |
| `DEMO_EXECUTION_MODE` | 必须理解 | 当前请固定为 `simulate` |
| `DEMO_WRITE_ENABLED` | 必须理解 | 即使是本地模拟转账，也需要设成 `true` 才能执行 |
| `DEMO_OPERATOR_PIN` | 可选 | 如果你想给 Operator Console 单独设置登录 PIN，再额外加这一项 |
| `DEMO_APPROVAL_PIN` | 当前模板已提供 | 本地授权 PIN，同时也是 Operator Console 登录 PIN 的回退值 |
| `DEMO_DATA_DIR` | 建议理解 | 本地数据目录，保存提案、余额、白名单等状态 |

### 与钱包身份相关的变量

| 变量名 | 是否必填 | 作用 |
| --- | --- | --- |
| `DEMO_PRIVATE_KEY` | 可空 | 测试钱包私钥。为空时地址显示为 `UNCONFIGURED` |
| `SEPOLIA_RPC_URL` | 可空 | 读取测试链信息的 RPC。当前模拟模式可以为空 |
| `DEMO_CHAIN_ID` | 不建议改 | Sepolia 的链 ID，默认 `11155111` |

### 与风控相关的变量

| 变量名 | 默认值 | 作用 |
| --- | --- | --- |
| `DEMO_MAX_TRANSFER_ETH` | `0.5` | 单笔最大可转金额 |
| `DEMO_REQUIRE_WHITELIST` | `true` | 是否启用收款白名单 |
| `DEMO_REQUIRE_LOCAL_AUTH` | `false` | 是否要求二次本地 PIN 授权 |
| `DEMO_PROPOSAL_TTL_MINUTES` | `30` | 提案过期时间 |
| `DEMO_LOCAL_AUTH_TTL_MINUTES` | `5` | 本地授权窗口有效时间 |

### 与本地余额相关的变量

| 变量名 | 默认值 | 作用 |
| --- | --- | --- |
| `DEMO_SIMULATED_BALANCE_ETH` | `50` | 只在第一次初始化本地钱包状态时作为初始余额使用 |

注意：

- 运行一段时间后，真实使用中的模拟余额会保存在 `data/wallet_state.json`
- 不是每次都重新从 `.env` 覆盖

## 6. 先启动人工后台 Operator Console

启动命令：

```bash
uv run cobo-wallet-operator
```

启动后你会在终端里看到类似输出（有一定的运行延迟是正常的，请耐心等待）：

```text
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

注意：

- 如果 `8501` 被占用，Streamlit 可能会自动换成 `8502`、`8503` 等端口
- 以终端打印出来的地址为准

然后你需要做这些事：

1. 打开浏览器访问终端里的本地地址
2. 输入 `DEMO_OPERATOR_PIN`；如果你没单独设置它，就输入 `DEMO_APPROVAL_PIN`（当前模板默认 `123456`）
3. 进入后台页面

### Operator Console 每个页面是做什么的

`Dashboard`

- 看钱包总览
- 看最近提案
- 看最近交易
- 看最近人工资金调整

`Wallet`

- 配置 `SEPOLIA_RPC_URL`
- 配置或替换 `DEMO_PRIVATE_KEY`

`Balance Lab`

- 人工给模拟余额加钱
- 人工减钱
- 直接把余额设成某个值

`Whitelist`

- 管理白名单地址

`Address Book`

- 管理联系人名称、地址、别名

`Policy`

- 打开或关闭写入能力
- 控制是否启用白名单
- 控制是否启用本地二次授权
- 设置单笔限额

### 第一次打开后台后建议检查这几项

- `DEMO_EXECUTION_MODE` 是不是 `simulate`
- `DEMO_WRITE_ENABLED` 是不是 `true`
- 模拟余额是不是你想要的值，例如 `50 ETH`
- 是否需要先加入白名单
- 是否已经配置联系人

## 7. 如何把项目接入 Codex

如果你要让 Codex 直接调用这个钱包 MCP，推荐在项目根目录执行下面的命令。

macOS / Linux:

```bash
PROJECT_DIR="$(pwd)"
codex mcp add cobo-wallet -- uv run --project "$PROJECT_DIR" cobo-wallet-mcp
```

Windows PowerShell:

```powershell
$PROJECT_DIR = $PWD.Path
codex mcp add cobo-wallet -- uv run --project $PROJECT_DIR cobo-wallet-mcp
```

然后检查是否注册成功：

```bash
codex mcp get cobo-wallet
```

### 这一段你要理解什么

- 一旦注册成功，通常不需要你手动再开一个终端运行 `uv run cobo-wallet-mcp`
- Codex 会在需要时自动拉起这个 MCP 进程
- 你平时真正需要手动开的，是 `Operator Console`

## 8. 接入 Codex 后可以怎么用

接入Codex：

```bash
codex
```

### 推荐的测试指令

1. `显示我的钱包总览`
2. `列出联系人`（如果没开启白名单）
3. `列出我白名单的地址` (如果开启了白名单)
4. `帮我向 小明 转 0.01 ETH`（选择地址进行转账，白名单有包括小明、小红的地址）
5. `查看最近10条转账记录`

## 9. Agent 能做什么，不能做什么

### Agent 可以直接做

- 查询钱包总览
- 查询余额
- 显示收款信息
- 创建提案
- 确认提案
- 取消提案
- 执行模拟转账
- 查看交易历史
- 查看提案列表

### Agent 不能直接做

- 修改私钥
- 修改 RPC
- 修改模拟余额
- 修改白名单
- 修改地址簿
- 修改策略开关

这些敏感操作必须去 `Operator Console` 做。 这不是 bug，而是当前项目的权限边界设计。

## 10. 如果你想先不用 Codex，也可以直接用 CLI 自测

这个项目自带一个本地 CLI。

### 查看钱包信息

```bash
uv run cobo-wallet-demo account
uv run cobo-wallet-demo balance
uv run cobo-wallet-demo policy
```

### 查看联系人和白名单

```bash
uv run cobo-wallet-demo recipients
uv run cobo-wallet-demo list-whitelist
```

### 创建和执行一笔模拟转账

先创建提案：

```bash
uv run cobo-wallet-demo propose --to burn --amount 0.01
```

记下返回里的 `proposal_id`，然后确认：

```bash
uv run cobo-wallet-demo confirm-proposal --proposal-id proposal_xxxxxxxx
```

然后执行：

```bash
uv run cobo-wallet-demo confirm --proposal-id proposal_xxxxxxxx
```

最后查看历史：

```bash
uv run cobo-wallet-demo list-transactions --limit 10
```

### 查看单条提案

```bash
uv run cobo-wallet-demo get-proposal --proposal-id proposal_xxxxxxxx
```

### 取消提案

```bash
uv run cobo-wallet-demo cancel-proposal --proposal-id proposal_xxxxxxxx
```

## 11. 最推荐的新手启动顺序

如果你完全不想思考，直接照着做，最简单就是下面这套。

1. `git clone` 项目并进入目录
2. 运行 `uv sync`
3. 执行 `cp .env.example .env`，或者手动按 README 里的配置块创建 `.env`
4. 运行 `uv run cobo-wallet-operator`
5. 打开浏览器，输入 `DEMO_OPERATOR_PIN`；如果没单独设置，就输入 `DEMO_APPROVAL_PIN`（当前模板默认 `123456`）
6. 在项目根目录执行 Codex 注册命令
7. 在 Codex 里说：
   - `显示我的钱包总览`
   - `帮我向 小明 转 0.01 ETH`
   - `查看最近10条转账记录`

如果你能走到这一步，就说明项目已经成功跑起来了。

## 12. 补充说明

如果你想看更详细的设计文档，可以再查看：

- `docs/requirement-1-user-personas.md`
- `docs/requirements-2-solved-problem.md`
- `docs/requirements-3-architecture.md`
- `docs/tool-test-report.md`
- `docs/ai-collaboration.md`

但如果你的目标只是“先把项目运行起来”，只看本 README 就够了。
