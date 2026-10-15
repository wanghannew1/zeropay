# ZeroPay 个人工资发放查询

面向业务员的网页工具：输入身份证号即可查询 TC93 工资明细，自动关联 TC8M 的发放状态与经办年月，并支持 Excel 导出。当前无登录鉴权，建议部署在内网使用。

## 功能特性

- 按身份证号（18 位）查询个人工资明细
- 发放状态以徽章形式展示，直观区分待确认 / 确认可发放 / 已发放
- TC8M 无匹配记录时显示为留空，语义即"未发放"
- 支持将查询结果导出为 Excel
- 非法输入（非 18 位、含非法字符等）在前端与接口层均做校验

## 环境要求

- 操作系统：Linux（已在 Ubuntu 上验证）
- Python 3.8 及以上
- Oracle Instant Client 23.4 已安装在 `/opt/oracle/instantclient_23_4`，必须以 **thick 模式** 连接（Oracle 11g 不支持 thin 模式）
- 网络可达 Oracle 数据库 `172.16.0.60:1521/orcl`
- 本机端口 `5001` 空闲（或按后文说明修改）

## 部署步骤

```bash
# 1. 拉取代码
git clone git@gitee.com:wanghannew1/zeropay.git
cd zeropay

# 2. （可选）创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 准备配置文件（.env 含数据库口令，已被 .gitignore 忽略，禁止提交）
cp .env.example .env
# 编辑 .env，将 DB_PASSWORD=<数据库口令> 替换为真实口令

# 5. 赋予启动脚本执行权限
chmod +x start.sh

# 6. 启动服务（脚本会先 export LD_LIBRARY_PATH=/opt/oracle/instantclient_23_4 再启动 python3 app.py）
./start.sh

# 7. 浏览器访问
#    http://<服务器IP>:5001
```

## Windows 部署

Windows 下双击 `start.bat`（内部调用 `start.ps1`）即可自动完成依赖安装并启动：

1. 安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)（推荐，脚本自动管理 `.venv`；无 uv 时回退系统 Python + pip）与 Python 3.8+
2. 安装 Oracle Instant Client 23.4 **for Windows**，解压到如 `C:\oracle\instantclient_23_4`，并设置环境变量 `ORACLE_CLIENT_LIB_DIR` 指向该目录（脚本会自动探测 `C:\oracle\instantclient_23_4`、`C:\instantclient_23_4`、项目目录下 `instantclient_23_4`）
3. `copy .env.example .env` 并将 `DB_PASSWORD` 填为真实数据库口令
4. 双击 `start.bat`（或在 PowerShell 中执行 `.\start.ps1`）
5. 浏览器访问 `http://localhost:5001`

依赖通过 `uv pip install -r requirements.txt`（清华镜像）安装，已装齐则跳过。若 PowerShell 提示执行策略限制，先执行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`（使用 `start.bat` 启动则无需此步）。

## 以 systemd 服务常驻（推荐生产）

在服务器上创建 `zeropay.service`（内容如下）：

```ini
[Unit]
Description=ZeroPay 个人工资发放查询
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/github/ZeroPay
ExecStart=/home/ubuntu/github/ZeroPay/start.sh
Environment=LD_LIBRARY_PATH=/opt/oracle/instantclient_23_4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> `User=` 请按实际运行用户修改；`WorkingDirectory` 与 `ExecStart` 请按实际部署路径修改。

启用并启动：

```bash
sudo cp zeropay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zeropay
sudo systemctl status zeropay
```

## 验证部署

使用仓库自带的 `verify.py` 做端到端校验：

```bash
ZP_TEST_CERT=<测试身份证号> python3 verify.py
```

可选环境变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `ZP_TEST_CERT` | 测试用身份证号（必填） | 无 |
| `ZP_TEST_ROWS` | 期望返回行数 | 359 |
| `ZP_TEST_BLANK` | 期望"留空=未发放"行数 | 24 |
| `ZP_TEST_NAME` | 期望姓名（可选断言） | 不校验 |
| `ZP_TEST_AAC001` | 期望 AAC001（可选断言） | 不校验 |

脚本会断言：行数符合预期、无重复 ATC930、留空未发放行数符合预期、状态取值属于 `{待确认, 确认可发放, 已发放}` 或 `部分发放(X/Y)` 形式。

快速接口验证：

```bash
curl -s "http://127.0.0.1:5001/api/salary?cert=<身份证号>"
```

## 业务员使用说明

1. 打开浏览器，访问 `http://<服务器IP>:5001`
2. 在查询框输入 18 位身份证号，点击"查询"
3. 页面以表格展示该人员的工资明细，可直接在页面查看
4. 如需存档或转发，点击"导出 Excel"下载 `.xlsx` 文件

表格列：姓名、个人编号、员工号、结算单元、工资所属年月、发放批次、本次工资总额、本次应发工资、本次实发金额、本次个人所得税、发放状态、经办年月（来自 TC8M）。

**发放状态含义：**

| 状态 | 含义 |
|---|---|
| 待确认 | TC8M.ATC8M3 = 0，批次已录入但尚未确认 |
| 确认可发放 | TC8M.ATC8M3 = 1，已确认待银行划转 |
| 已发放 | TC8M.ATC8M3 = 2，银行已划转完成 |
| （留空） | 该笔工资在 TC8M 中无发放批次记录，即未发放 |
| 部分发放(1/2) | 同一组合跨银行状态不一致，括号内为 MIN/MAX |

## 查询口径（技术备注）

- TC93 按 `AAC002`（身份证号）过滤
- `LEFT JOIN` TC8M，关联键为 `ATB930 + ATC931 + ATC937`
- TC8M 先按该组合 `GROUP BY`，取 `MIN(ATC8M3)`、`MAX(ATC8M3)`、`MAX(ATC8G7)` 再关联，不按发放银行 `BBB002` 拆分，保证每笔工资恰好一行
- 取 `ATC8M3` 作为发放状态、`ATC8G7` 作为经办年月

## 常见问题

| 问题 | 处理 |
|---|---|
| `DPY-3010 connections to this database server version are not supported in thin mode` | Oracle 11g 必须 thick 模式。确认 `db.py` 中 `oracledb.init_oracle_client` 已执行，且 `LD_LIBRARY_PATH` 已设置。用 `start.sh` 启动即可。 |
| `DPI-1047 Cannot locate a 64-bit Oracle Client library` / `libnnz.so: cannot open shared object file` | `LD_LIBRARY_PATH` 未包含 `/opt/oracle/instantclient_23_4`。用 `start.sh` 启动，或手动 `export LD_LIBRARY_PATH=/opt/oracle/instantclient_23_4:$LD_LIBRARY_PATH`。 |
| 端口冲突：`Address already in use` | `app.py` 默认监听 5001。如需修改，编辑 `app.py` 末尾 `app.run(host="0.0.0.0", port=5001, debug=False)` 中的 `port`。 |
| 查询很慢 / 超时 | 检查到 `172.16.0.60` 的网络是否可达，以及 `.env` 中 `DB_HOST` / `DB_PORT` / `DB_SERVICE_NAME` / `DB_USER` / `DB_PASSWORD` 是否正确。 |
| `.env` 不小心被提交到仓库 | 立即轮换数据库口令。`.gitignore` 已忽略 `.env`，但历史提交中的口令仍可见，需修改密码并 `git rm --cached .env`。 |

## 项目结构

```
ZeroPay/
├── app.py              # Flask 主应用，路由与接口定义，监听 0.0.0.0:5001
├── queries.py          # SQL 查询与结果组装（TC93 LEFT JOIN TC8M）
├── db.py               # Oracle 连接池（thick 模式）
├── config.py           # 从 .env 读取配置
├── templates/
│   └── index.html      # 前端页面（查询框、结果表格、导出按钮）
├── start.sh            # Linux 启动脚本：设置 LD_LIBRARY_PATH 后 exec python3 app.py
├── start.ps1           # Windows 启动脚本：uv pip 安装依赖并启动
├── start.bat           # Windows 双击启动入口（调用 start.ps1，绕过执行策略）
├── verify.py           # 端到端验证脚本（断言行数、状态取值等）
├── requirements.txt    # Python 依赖：flask, oracledb, openpyxl, python-dotenv
├── .env.example        # 配置模板，复制为 .env 后填入真实口令
└── .gitignore          # 忽略 .env、__pycache__、.venv、*.xlsx 等
```
