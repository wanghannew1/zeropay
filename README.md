# ZeroPay 个人工资发放查询

面向业务员的网页工具：输入身份证号即可查询 TC93 工资明细，自动关联 TC8M 的发放状态与经办年月，并支持 Excel 导出。当前无登录鉴权，建议部署在内网使用。

## 功能特性

- 按身份证号（18 位）查询个人工资明细
- 发放状态以徽章形式展示，直观区分待确认 / 确认可发放 / 已发放
- TC8M 无匹配记录时显示为留空，语义即"未发放"
- 支持将查询结果导出为 Excel
- 非法输入（非 18 位、含非法字符等）在前端与接口层均做校验
- 跨结算单元员工工资明细导出：支持「查询范围」开关（仅跨结算单元 / 全部人员），筛选历史上工资跨越多个结算单元的员工（约 5,897 人）或 TC93 全体员工（约 39,370 人），支持按发薪年月（所属年月）、发放年月（经办年月）与工资状态过滤，导出 TC93 全字段 + TC8M 关键 8 字段共 188 列的 `.xlsx`；单表超过 Excel 上限（1,048,576 行）时接口返回 400 错误、不生成文件

## 环境要求

- 操作系统：Linux（已在 Ubuntu 上验证）
- Python 3.8 及以上
- Oracle Instant Client 23.4 **Basic（完整包）**：启动脚本会自动从 Oracle 官网下载并解压到项目内 `instantclient_23_4/`，无需手动安装（Oracle 11g 不支持 thin 模式，必须 thick）。注意不能用 Basic Light（仅西文字符集，本库为 ZHS16GBK 会中文乱码）。详见「Oracle Instant Client 下载」一节
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

> ⚠️ **安装路径请勿包含中文**（如 `C:\Users\张三\zeropay` 是错误的），建议解压到纯英文路径，例如 `C:\zeropay`。含中文路径会导致 Python/Oracle 客户端依赖加载失败或路径解析异常。

Windows 下双击 `start.bat`（内部调用 `start.ps1`）即可自动完成依赖安装并启动：

1. 安装 [uv](https://docs.astral.sh/uv/getting-started/installation/)（推荐，脚本自动管理 `.venv`；无 uv 时回退系统 Python + pip）与 Python 3.8+
2. **无需手动安装 Oracle 客户端**：`start.ps1` 启动时自动从 Oracle 官网下载 Instant Client Basic (~120MB) 并解压到项目内 `instantclient_23_4\`；如已有客户端，放置到项目 `instantclient_23_4\` 或 `C:\oracle\instantclient_23_4` 亦可（详见「Oracle Instant Client 下载」）
3. `copy .env.example .env` 并将 `DB_PASSWORD` 填为真实数据库口令
4. 双击 `start.bat`（或在 PowerShell 中执行 `.\start.ps1`）
5. 浏览器访问 `http://localhost:5001`

依赖通过 `uv pip install -r requirements.txt`（清华镜像）安装，已装齐则跳过。若 PowerShell 提示执行策略限制，先执行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`（使用 `start.bat` 启动则无需此步）。

## Oracle Instant Client 下载（自动下载失败时手动安装）

启动脚本默认从 Oracle 官网直链自动下载 **Basic 完整包**（不能用 Basic Light，本库字符集 ZHS16GBK，Light 会中文乱码）。若网络不通或下载失败，可手动下载后按下述任一方式放置：

| 平台 | 直链（约 120MB） |
|---|---|
| Windows x64 | `https://download.oracle.com/otn_software/nt/instantclient/2340000/instantclient-basic-windows.x64-23.4.0.24.05.zip` |
| Linux x64 | `https://download.oracle.com/otn_software/linux/instantclient/2340000/instantclient-basic-linux.x64-23.4.0.24.05.zip` |

官方下载页（如直链失效，到此选 23.4 版本 Basic 包）：
- Windows: https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html
- Linux: https://www.oracle.com/database/technologies/instant-client/linux-downloads.html

> 用浏览器或 wget/curl 下载时需接受 Oracle 许可协议；命令行下载可加请求头 `Cookie: oraclelicense=accept-securebackup-cookie`。

手动放置方式（任选其一，脚本按顺序探测）：

1. **项目内 zip**：把 zip 原样放到项目根目录，命名 `instantclient-basic-win64-23.4.zip`（Windows）或 `instantclient-basic-linux64-23.4.zip`（Linux），脚本会直接解压使用，不再联网
2. **项目内目录**：把 zip 解压后的目录改名（或移动）为项目根目录下的 `instantclient_23_4/`（确保里面有 `oci.dll` / `libclntsh.so`）
3. **系统目录**：解压到 `C:\oracle\instantclient_23_4` 或 `/opt/oracle/instantclient_23_4`
4. **内网镜像**：设置环境变量 `ZERO_PAY_CLIENT_ZIP_URL=<zip 地址>`（可为内网 HTTP/共享路径），脚本改为从该地址下载

也可设置 `ORACLE_CLIENT_LIB_DIR` 环境变量直接指定客户端目录，优先级最高。

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

### 跨结算单元员工工资明细导出

页面下方第二张卡片（深灰色标题）用于批量导出"工资跨多个结算单元"的员工明细。

**操作步骤：**

1. 在"发薪年月（所属年月）"输入框填入 6 位 `YYYYMM`（如 `202609`），留空表示不限月份
2. 在"发放年月（经办年月）"输入框填入 6 位 `YYYYMM`（如 `202510`），留空表示不限月份
3. 在"查询范围"下拉中选择导出人员范围（默认"仅跨结算单元"）
4. 在"工资状态"下拉中选择筛选口径（默认"仅未发放"）
5. 点击"导出 Excel（全字段）"，浏览器会自动开始下载 `.xlsx`

> **注意：** 填写发放年月后，无发放记录（未发放）的工资行没有经办年月，会被排除；因此「仅未发放」与「发放年月」同时使用会得到空结果。

**工资状态三档口径（按筛选严格度由严到宽）：**

| 选项 | 含义 | 适用场景 |
|---|---|---|
| 仅未发放 | TC8M 中完全没有该笔工资的发放记录（状态留空） | 只想看"彻底没发过"的工资 |
| 未发工资（未达已发放） | 无发放记录，或状态尚未达到"已发放"（含待确认 / 确认可发放 / 部分发放） | 想看"还没到账"的工资 |
| 全部状态 | 不做状态过滤 | 全量核对、审计 |

**查询范围两档语义：**

| 选项 | 含义 | 约人数 |
|---|---|---|
| 仅跨结算单元（默认） | 历史上 TC93 中工资跨多个结算单元的员工 | 约 5,897 人 |
| 全部人员 | TC93 全体员工（不按跨结算单元过滤） | 约 39,370 人 |

**各范围实测数据量（含表头，单表上限 1,048,576 行）：**

| 范围 | 全部状态 | 仅未发放 | 未发工资 |
|---|---|---|---|
| 仅跨结算单元 | 479,209 行 | 61,911 行 | 189,706 行 |
| 全部人员 | 1,172,557 行（**超 Excel 上限，必须加筛选**） | 235,604 行 | 563,945 行 |

> ⚠️ **Excel 单表上限保护：** 单表最多 1,048,576 行（含表头）。数据量超限时接口返回 HTTP 400 `{"ok": false, "error": "数据量超过 Excel 单表上限（1048576 行），请增加筛选条件"}`，不会生成/下载文件。典型超限场景：全部人员 + 全部状态（约 117 万行）。请配合发薪年月、发放年月或工资状态筛选缩小范围。

**下载行为：** 点击导出后浏览器会打开新标签页，服务端生成 xlsx 完成后自动开始下载。全量导出文件可能数百 MB、生成需数分钟，请耐心等待，不要重复点击。

**文件名格式（按查询范围区分前缀）：**

- 仅跨结算单元：`跨结算单元工资明细_发薪{YYYYMM|全部}_发放{YYYYMM|全部}_{仅未发放|未发工资|全部状态}.xlsx`
- 全部人员：`全部人员工资明细_发薪{YYYYMM|全部}_发放{YYYYMM|全部}_{仅未发放|未发工资|全部状态}.xlsx`

| 筛选组合 | 文件名示例 |
|---|---|
| 仅跨结算单元 + 发薪 202609 + 发放 202510 + 未发工资 | `跨结算单元工资明细_发薪202609_发放202510_未发工资.xlsx` |
| 仅跨结算单元 + 发薪不限 + 发放不限 + 仅未发放 | `跨结算单元工资明细_发薪全部_发放全部_仅未发放.xlsx` |
| 仅跨结算单元 + 发薪 202609 + 发放不限 + 全部状态 | `跨结算单元工资明细_发薪202609_发放全部_全部状态.xlsx` |
| 全部人员 + 发薪 202609 + 发放 202510 + 仅未发放 | `全部人员工资明细_发薪202609_发放202510_仅未发放.xlsx` |
| 全部人员 + 发薪不限 + 发放不限 + 未发工资 | `全部人员工资明细_发薪全部_发放全部_未发工资.xlsx` |

## 查询口径（技术备注）

- TC93 按 `AAC002`（身份证号）过滤
- `LEFT JOIN` TC8M，关联键为 `ATB930 + ATC931 + ATC937`
- TC8M 先按该组合 `GROUP BY`，取 `MIN(ATC8M3)`、`MAX(ATC8M3)`、`MAX(ATC8G7)` 再关联，不按发放银行 `BBB002` 拆分，保证每笔工资恰好一行
- 取 `ATC8M3` 作为发放状态、`ATC8G7` 作为经办年月

### 跨结算单元导出（`/api/cross-unit/export`）

**查询范围（`scope` 参数，可选，默认 `cross_unit`）：**

| `scope` 取值 | 含义 | 人员过滤逻辑 |
|---|---|---|
| `cross_unit`（默认） | 仅跨结算单元 | 历史上 TC93 中 `ATB930`（结算单元流水号）满足 `MIN(ATB930) <> MAX(ATB930)`（按 `AAC002` 身份证号 `GROUP BY`）的员工，即工资跨越多个结算单元的员工 |
| `all` | 全部人员 | TC93 全体员工，不按跨结算单元过滤（即 `AAC002` 不做 `HAVING MIN<>MAX` 过滤） |

其他筛选（发薪年月 `month`、发放年月 `pay_month`、工资状态 `status`）在两种范围下语义完全相同，可任意组合。非法 `scope` 值 → HTTP 400 `{"ok": false, "error": "查询范围参数错误"}`。

**Excel 单表上限保护：** 单表最多 1,048,576 行（含表头）。服务端在生成文件前会先统计数据量，超限时直接返回 HTTP 400 `{"ok": false, "error": "数据量超过 Excel 单表上限（1048576 行），请增加筛选条件"}`，**不会生成/下载文件**（fail-closed，不会产出截断的不完整文件）。典型超限场景：`scope=all` + `status=all`（约 1,172,557 行）。

**关联键（TC93 ↔ TC8M 聚合）：** `ATB930`（结算单元流水号）+ `ATC931`（工资所属年月）+ `ATC937`（工资发放次数/发薪批次）。每笔工资恰好一行。

**TC8M 聚合口径：** 按上述关联键 `GROUP BY`，
- 发放状态：`MIN(ATC8M3)` → `ATC8M3_MIN`、`MAX(ATC8M3)` → `ATC8M3_MAX`
- 经办年月：`MAX(ATC8G7)`
- 发放银行：`BBB002` 以逗号拼接合并（`LISTAGG`）→ `BBB002`
- 发放总额合计：`SUM(ATC8M2)` → `ATC8M2`
- 发放人数：`MAX(ATC8M1)` → `ATC8M1`
- 发放日：`MAX(ATB90AB)` → `ATB90AB`
- 发放状态（展示用）：由 MIN/MAX 派生，与个人查询口径一致

**月份筛选：**

- **发薪年月（`month`）：** 作用于 `TC93.ATC931`（工资所属年月）。在当前数据中 `ATC931` 与 `ATC932`（工资发放年月）恒等，但接口按 `ATC931` 过滤。留空 = 不限月份。
- **发放年月（`pay_month`）：** 作用于 TC8M 聚合后的 `MAX(ATC8G7)`（经办年月），与导出列中的"经办年月(ATC8G7)"一致。填写后仅保留经办年月等于该值的工资行。留空 = 不限月份。
  - 无发放记录（未发放）的行没有经办年月，会被排除；因此「仅未发放」与「发放年月」同时使用会得到空结果。
  - 数据参考：TC8M 经办年月约 98% 非空、68 个取值。
  - 格式错误（非 6 位 YYYYMM）→ HTTP 400 `{"ok": false, "error": "发放年月格式错误，应为YYYYMM（如202510）"}`。

**发薪年月 vs 发放年月：** 发薪年月 = 工资所属年月 `ATC931`（发的是哪个月的工资）；发放年月 = 经办年月 `ATC8G7`（哪个月处理发放）。两个筛选可组合（AND）。

**状态筛选三档语义：**

| `status` 取值 | 含义 |
|---|---|
| `unpaid`（默认） | 仅未发放：TC8M 中无对应发放记录（状态留空） |
| `not_paid` | 未发工资（未达已发放）：无发放记录，或状态未达到"已发放"（含待确认 / 确认可发放 / 部分发放） |
| `all` | 全部状态，不做过滤 |

**列构成（共 188 列）：** TC93 全部 180 字段 + TC8M 关键 8 字段（发放状态、`ATC8M3_MIN`、`ATC8M3_MAX`、`ATC8G7`、`BBB002`、`ATB90AB`、`ATC8M2`、`ATC8M1`）。列名格式为 `中文名(字段名)`，由 `schema_cn.py` 提供映射。

**大整数处理：** 流水号等 16 位整数列按文本导出（Excel 对超过 15 位的数字会丢失精度）。

**量级参考（实测）：**

| 查询范围 | 人员 | 全部状态 | 仅未发放 | 未发工资 |
|---|---|---|---|---|
| 仅跨结算单元（`cross_unit`） | 约 5,897 人 | 479,209 行 | 61,911 行 | 189,706 行 |
| 全部人员（`all`） | 约 39,370 人 | 1,172,557 行（超 Excel 上限，必须加筛选） | 235,604 行 | 563,945 行 |

单月筛选（任一范围）约 6,000–9,000 行。全量导出文件可能数百 MB、生成需数分钟，建议优先使用发薪年月、发放年月或状态筛选缩小范围。

## 常见问题

| 问题 | 处理 |
|---|---|
| `DPY-3010 connections to this database server version are not supported in thin mode` | Oracle 11g 必须 thick 模式。确认 `db.py` 中 `oracledb.init_oracle_client` 已执行，且 `LD_LIBRARY_PATH` 已设置。用 `start.sh` 启动即可。 |
| `DPI-1047 Cannot locate a 64-bit Oracle Client library` / `libnnz.so: cannot open shared object file` | `LD_LIBRARY_PATH` 未包含 `/opt/oracle/instantclient_23_4`。用 `start.sh` 启动，或手动 `export LD_LIBRARY_PATH=/opt/oracle/instantclient_23_4:$LD_LIBRARY_PATH`。 |
| 端口冲突：`Address already in use` | `app.py` 默认监听 5001。如需修改，编辑 `app.py` 末尾 `app.run(host="0.0.0.0", port=5001, debug=False)` 中的 `port`。 |
| `start.ps1` 打开乱码、报"数组索引表达式丢失/字符串缺少终止符/缺少右括号" | 文件编码问题：`.ps1` 中文必须存为 **UTF-8 with BOM**，否则 Windows PowerShell 5.1 按 GBK 误读中文导致连锁语法错误。仓库已修复，请重新下载代码包或 `git pull` 后重试；不要用记事本"另存为 ANSI" |
| 查询很慢 / 超时 | 检查到 `172.16.0.60` 的网络是否可达，以及 `.env` 中 `DB_HOST` / `DB_PORT` / `DB_SERVICE_NAME` / `DB_USER` / `DB_PASSWORD` 是否正确。 |
| 跨结算单元导出很慢 / 文件很大 | 全量约 48 万行属正常（实测约 479,209 行），文件可能数百 MB、生成需数分钟。建议配合"发薪年月""发放年月"或"工资状态"筛选缩小范围后再导出。 |
| 导出报错"数据量超过 Excel 单表上限" | 单表最多 1,048,576 行（含表头），超限后接口返回 400 且不生成文件。典型场景：查询范围=全部人员 + 工资状态=全部状态（约 117 万行）。处理：① 加"发薪年月"或"发放年月"筛选缩小范围；② 或把查询范围切回"仅跨结算单元"（约 48 万行，不超限）。 |
| `.env` 不小心被提交到仓库 | 立即轮换数据库口令。`.gitignore` 已忽略 `.env`，但历史提交中的口令仍可见，需修改密码并 `git rm --cached .env`。 |

## 项目结构

```
ZeroPay/
├── app.py              # Flask 主应用，路由与接口定义，监听 0.0.0.0:5001
├── queries.py          # SQL 查询与结果组装（TC93 LEFT JOIN TC8M；跨结算单元导出查询）
├── db.py               # Oracle 连接池（thick 模式）
├── config.py           # 从 .env 读取配置
├── schema_cn.py        # TC93/TC8M 中文列名映射（188 列），gen_schema_cn.py 生成
├── gen_schema_cn.py    # 列名映射生成脚本（从数据库元数据生成 schema_cn.py）
├── templates/
│   └── index.html      # 前端页面（个人查询框 + 结果表格 + 跨结算单元导出卡片）
├── start.sh            # Linux 启动脚本：设置 LD_LIBRARY_PATH 后 exec python3 app.py
├── start.ps1           # Windows 启动脚本：uv pip 安装依赖并启动
├── start.bat           # Windows 双击启动入口（调用 start.ps1，绕过执行策略）
├── verify.py           # 端到端验证脚本（断言行数、状态取值等）
├── requirements.txt    # Python 依赖：flask, oracledb, openpyxl, xlsxwriter, python-dotenv
├── .env.example        # 配置模板，复制为 .env 后填入真实口令
└── .gitignore          # 忽略 .env、__pycache__、.venv、*.xlsx 等
```
