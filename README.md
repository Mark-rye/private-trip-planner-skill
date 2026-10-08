# 私人定制旅行规划专家（Codex Skill）

为个人、情侣、亲子和银发旅行生成手机优先的随身攻略，覆盖交通、住宿、餐饮、文化亮点、预约与预算，并输出可离线查看的比例尺示意地图。

## 主要改进

- 完整版逐项覆盖首屏、路线、速览、景区亮点、每日详程、住宿、餐厅、交通、费用预估、预订看板、预算报告、实用准备与来源；按用户示例的子模块和样例深度编写。
- `detail_level: complete` 校验缺少模块和逐日内容，不能把简短技术演示当作详细攻略交付。
- 已有完整 HTML 原稿可保留全部正文，增加逐日执行建议、冲突说明、章节导航、分地区比例尺地图，并将宽表格转为手机卡片。
- 地图按天分色，地点使用“天数-顺序”编号。
- 用地理坐标保留相对方向和距离，附北向标记及米/公里比例尺，虚线表示访问顺序。
- 手机单列自然滚动，按天切换，支持 375–430px 窄屏和长地点名称换行。
- 每日交通、住宿、餐饮、风险默认可见；文化历史可展开，保留攻略深度。
- 已订与已付分开；套餐已含项、可选项和取消项不重复计入基础预算。
- 自动汇总独立预订项数、已知金额、付款及人均金额；缺价不冒充完整总预算。
- 校验活动结束、转场与候车缓冲，拒绝时间不足的衔接。
- 使用结构化 `trip-data.json`，便于修改日期、地点和路线后重新渲染。
- 对开放时间、交通、票价、预约和签证等时效信息要求联网核验并保留来源。

## 安装

将本仓库克隆或复制到 Codex Skills 目录：

```bash
git clone https://github.com/Mark-rye/private-trip-planner-skill.git ~/.codex/skills/private-trip-planner
```

然后在 Codex 中使用：

```text
$private-trip-planner 为我规划 5 天京都亲子旅行，节奏轻松，公共交通为主，并生成交互地图。
```

## 地图渲染

准备符合 [`references/output-contract.md`](references/output-contract.md) 的 `trip-data.json` 后运行：

```bash
python3 scripts/render_map.py --input trip-data.json --output trip-map.html
```

先校验数据而不生成页面：

```bash
python3 scripts/render_map.py --input trip-data.json --validate-only
```

生成匿名技术演示（仅测试地图与数据接口，不是完整版攻略）：

```bash
python3 scripts/render_map.py --input assets/example-trip.json --output trip-map.html
```

阅读页内置 SVG 示意地图，不加载外部字体、脚本或地图瓦片，保存后可离线阅读。
比例尺表示约地理直线距离，不代表道路里程或交通耗时。出行事实与班次仍需联网核验。

完整攻略组织与账目规则见 [guide-blueprint.md](references/guide-blueprint.md)。
示例订单均为虚构数据，本仓库不包含私人攻略或支付凭证。

## 保留完整原稿制作手机版

先按蓝本检查原稿模块覆盖，并写出独立的逐日执行补充与待核验信息，再运行：

```bash
python3 scripts/render_reference.py --input original.html --enhancements notes.json --output mobile-guide.html
```

`notes.json` 字段见蓝本。正文不会被压缩成摘要，原页面脚本与外部资源默认被阻止；仅嵌入的图片可离线显示。原稿与生成的私人阅读页不应提交到公开仓库。再次出行前仍须按新日期核验票价、班次、签证与演出。
