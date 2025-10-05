# PhotoWatermarkGUI

基于 PyQt6 的跨平台桌面工具，可批量为图片添加文本水印并导出。满足《PhotoWatermarkGUI》PRD 中的首发版本（P0）需求，包括：

- 支持拖拽/选择图片及整个文件夹导入，展示缩略图列表与预览。
- 文本水印实时预览，支持透明度、字体大小调节和九宫格快捷定位，亦可拖拽定位。
- 导出时可选择输出目录、命名规则（原名/前缀/后缀）与输出格式（自动/JPEG/PNG）。
- 保存/加载模板并自动恢复上次会话设置。

## 环境准备

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 启动

```powershell
python -m photowatermark_gui.main
```

## 目录结构

```text
photowatermark_gui/
├── main.py              # 入口
├── app.py               # 主窗口及界面逻辑
├── models.py            # 导出/水印配置数据模型
├── services/            # 文件、模板与水印处理服务
└── widgets/             # 自定义控件（图片列表、预览）
```

## 已知限制
 
- 当前仅提供文本水印（图片水印等为后续可选高级功能）。
- 字体选择、颜色、描边等高阶样式暂未开放。

欢迎根据 PRD 迭代扩展更多高级能力。
