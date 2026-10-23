# 第三方依赖记录

记录日期：2026-10-22。版本与许可证取自本地实际安装包的 importlib.metadata，不代表 Replit/Linux 已验证。项目代码 LICENSE 不改变第三方许可。

| 直接依赖 | 实测版本 | 安装包声明 | 上游与使用范围 |
|---|---|---|---|
| Streamlit | 1.66.1 | Apache-2.0 | https://github.com/streamlit/streamlit；最小页面及 AppTest |
| requests | 2.34.2 | Apache-2.0 | https://github.com/psf/requests；仅兼容性加载，无来源请求 |
| scikit-learn | 1.9.1 | BSD-3-Clause | https://github.com/scikit-learn/scikit-learn；仅兼容性加载，无产品推理 |
| pytest | 9.1.1 | MIT | https://github.com/pytest-dev/pytest；仅开发测试 |

requirements.txt 固定本地运行依赖及传递依赖；requirements-public.lock 与其字节相同，仅供净化公开包的隔离 Build 安装；requirements-dev.txt 固定额外开发依赖。传递包各自的 LICENSE/NOTICE 随其安装分发包保留；本仓库不复制第三方 wheel 或虚拟环境。未来打包或再分发第三方代码时，须一并核对并保留相应完整声明，不能只依赖此摘要。

以上依赖记录来自 TSK-00A，当时没有引入外部数据集。TSK-02 的数据许可与署名追加如下；该阶段没有引入 OpenAlex 数据。仓库后来保存了待审 OpenAlex snapshot 元数据，但 Step 27.2 public synthetic ZIP 不包含 `data/` 下的 O*NET、OpenAlex 或 review-only bundle。下述 O*NET 署名仍用于仓库内的待审资料，不表示公共演示使用或发布了这些记录。

## O*NET® 31.0 数据库（TSK-02，2026-10-23）

本仓库的 [三职业审阅数据](data/onet/31.0/tsk-02-review/README.md) 派生自 [O*NET 31.0 Database](https://www.onetcenter.org/database.html)，原始提供者为美国劳工部 Employment and Training Administration（USDOL/ETA），由 National Center for O*NET Development 开发。依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 使用；适用范围依据 [数据库许可页](https://www.onetcenter.org/license_db.html) 和原 ZIP 的 `Read Me.txt` 核对。该范围是可下载数据库，不扩展至网站其他内容、标志或职业测评工具。O*NET® 是 USDOL/ETA 的商标。

FuturePath 所作改变：筛选三个职业，将 TSV 转成 JSON，增加项目本地软件样例 ID、结构校验、证据引用和隔离标记；未改写原始工作场景名称或原始评分，没有计算归一化值或补造缺值。这些改变未获 USDOL/ETA 批准、背书或测试。处理规则、数量和限制见 [验收报告](docs/tsk-02-acceptance.md)；保留原值和定位符可核查每项转换。

项目代码的 LICENSE 不替代上述数据许可。重新分发 JSON 时应连同其 README、来源版本、许可链接和修改说明一起提供。原始 ZIP 位于仓库外，未加入 Git；隔离报告同样包含受 CC BY 4.0 约束的源行。当前产物供人工审阅，尚未作为已审发布数据或正式独立许可审计结论。
