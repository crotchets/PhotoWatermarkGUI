"""Main window for PhotoWatermarkGUI."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PIL import Image

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .models import ExportSettings, WatermarkSettings
from .services import image_loader
from .services.templates import TemplateManager
from .services.watermark import (
    ALLOWED_INPUT_SUFFIXES,
    compose_watermark,
    compute_output_path,
    scale_image,
)
from .widgets.image_list import ImageListWidget
from .widgets.preview import ImagePreview


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("PhotoWatermarkGUI")
        self.resize(1280, 820)

        self.template_manager = TemplateManager()
        self.watermark_settings = WatermarkSettings()
        self.export_settings = ExportSettings()

        self.images: List[Path] = []
        self.current_image: Optional[Path] = None

        self._init_ui()
        self._restore_last_session()
        self._refresh_template_list()

    def _init_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        self.image_list = ImageListWidget(self._add_images, self._remove_images)
        self.image_list.itemSelectionChanged.connect(self._handle_list_selection)
        left_layout.addWidget(self.image_list, stretch=1)
        self.batch_export_button = QPushButton("批量导出全部")
        left_layout.addWidget(self.batch_export_button)
        splitter.addWidget(left_container)
        splitter.setStretchFactor(0, 1)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(1, 3)

        toolbar_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.currentTextChanged.connect(self._load_template)
        toolbar_layout.addWidget(QLabel("模板："))
        toolbar_layout.addWidget(self.template_combo, 2)
        self.save_template_btn = QPushButton("保存模板")
        self.rename_template_btn = QPushButton("重命名")
        self.delete_template_btn = QPushButton("删除")
        self.export_toolbar_button = QPushButton("导出图片")
        toolbar_layout.addWidget(self.save_template_btn)
        toolbar_layout.addWidget(self.rename_template_btn)
        toolbar_layout.addWidget(self.delete_template_btn)
        toolbar_layout.addWidget(self.export_toolbar_button)
        right_layout.addLayout(toolbar_layout)

        self.preview = ImagePreview(self._on_preview_position_changed)
        right_layout.addWidget(self.preview, stretch=5)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        controls_container = QWidget()
        scroll_area.setWidget(controls_container)
        controls_layout = QVBoxLayout(controls_container)
        right_layout.addWidget(scroll_area, stretch=3)

        controls_layout.addWidget(self._build_import_group())
        controls_layout.addWidget(self._build_watermark_group())
        controls_layout.addWidget(self._build_position_group())
        controls_layout.addWidget(self._build_export_group())
        controls_layout.addStretch()

        self.save_template_btn.clicked.connect(self._save_template)
        self.rename_template_btn.clicked.connect(self._rename_template)
        self.delete_template_btn.clicked.connect(self._delete_template)
        self.export_toolbar_button.clicked.connect(self._export_all)
        self.batch_export_button.clicked.connect(self._export_all)

        self._update_export_buttons()
        self._update_quality_controls()
        self._update_scale_controls()

        import_action = QAction("导入图片", self)
        import_action.triggered.connect(self._prompt_import_images)
        folder_action = QAction("导入文件夹", self)
        folder_action.triggered.connect(self._prompt_import_folder)
        self.addAction(import_action)
        self.addAction(folder_action)
        import_action.setShortcut("Ctrl+I")
        folder_action.setShortcut("Ctrl+Shift+I")

    def _build_import_group(self) -> QWidget:
        group = QGroupBox("文件导入")
        layout = QVBoxLayout(group)
        tips = QLabel(
            "支持拖拽图片或文件夹到左侧列表，也可使用按钮导入。支持格式：" + ", ".join(sorted(ALLOWED_INPUT_SUFFIXES))
        )
        tips.setWordWrap(True)
        layout.addWidget(tips)
        buttons_layout = QHBoxLayout()
        self.import_button = QPushButton("选择图片…")
        self.import_folder_button = QPushButton("选择文件夹…")
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(self.import_folder_button)
        layout.addLayout(buttons_layout)
        self.import_button.clicked.connect(self._prompt_import_images)
        self.import_folder_button.clicked.connect(self._prompt_import_folder)
        return group

    def _build_watermark_group(self) -> QWidget:
        group = QGroupBox("水印配置")
        form = QFormLayout(group)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("输入水印文本，可多行")
        self.text_edit.setPlainText(self.watermark_settings.text)
        self.text_edit.textChanged.connect(self._on_text_changed)
        form.addRow("文本内容", self.text_edit)

        opacity_container = QWidget()
        opacity_layout = QHBoxLayout(opacity_container)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.watermark_settings.opacity)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(self.watermark_settings.opacity)
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        self.opacity_spin.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider, stretch=3)
        opacity_layout.addWidget(self.opacity_spin, stretch=1)
        form.addRow("透明度", opacity_container)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 200)
        self.font_size_spin.setValue(self.watermark_settings.font_size)
        self.font_size_spin.valueChanged.connect(self._on_font_size_changed)
        form.addRow("字体大小", self.font_size_spin)

        return group

    def _build_position_group(self) -> QWidget:
        group = QGroupBox("位置与布局")
        layout = QVBoxLayout(group)

        grid = QGridLayout()
        positions = [
            ("左上", QPointF(0.0, 0.0)),
            ("上中", QPointF(0.5, 0.0)),
            ("右上", QPointF(1.0, 0.0)),
            ("左中", QPointF(0.0, 0.5)),
            ("中心", QPointF(0.5, 0.5)),
            ("右中", QPointF(1.0, 0.5)),
            ("左下", QPointF(0.0, 1.0)),
            ("下中", QPointF(0.5, 1.0)),
            ("右下", QPointF(1.0, 1.0)),
        ]
        for index, (label, ratio) in enumerate(positions):
            button = QPushButton(label)
            row, col = divmod(index, 3)
            button.clicked.connect(lambda checked, r=ratio: self._apply_position(r))
            grid.addWidget(button, row, col)
        layout.addLayout(grid)
        layout.addWidget(QLabel("提示：可在预览图中拖拽水印到任意位置。"))
        return group

    def _build_export_group(self) -> QWidget:
        group = QGroupBox("导出设置")
        form = QFormLayout(group)

        output_container = QWidget()
        output_layout = QHBoxLayout(output_container)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        browse_btn = QPushButton("浏览…")
        browse_btn.clicked.connect(self._choose_output_dir)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(browse_btn)
        form.addRow("输出目录", output_container)

        naming_container = QWidget()
        naming_layout = QHBoxLayout(naming_container)
        self.naming_group = QButtonGroup(self)
        self.naming_original = QRadioButton("原名")
        self.naming_prefix = QRadioButton("前缀")
        self.naming_suffix = QRadioButton("后缀")
        for button in (self.naming_original, self.naming_prefix, self.naming_suffix):
            self.naming_group.addButton(button)
            naming_layout.addWidget(button)
        self.naming_original.setChecked(True)
        form.addRow("命名规则", naming_container)

        self.prefix_edit = QLineEdit(self.export_settings.prefix)
        self.suffix_edit = QLineEdit(self.export_settings.suffix)
        self.prefix_edit.setEnabled(False)
        self.suffix_edit.setEnabled(False)
        form.addRow("前缀", self.prefix_edit)
        form.addRow("后缀", self.suffix_edit)

        self.naming_original.toggled.connect(self._update_naming_mode)
        self.naming_prefix.toggled.connect(self._update_naming_mode)
        self.naming_suffix.toggled.connect(self._update_naming_mode)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["自动", "JPEG", "PNG"])
        self.format_combo.currentIndexChanged.connect(self._update_output_format)
        form.addRow("输出格式", self.format_combo)

        quality_container = QWidget()
        quality_layout = QHBoxLayout(quality_container)
        quality_layout.setContentsMargins(0, 0, 0, 0)
        self.jpeg_quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.jpeg_quality_slider.setRange(0, 100)
        self.jpeg_quality_slider.setValue(self.export_settings.jpeg_quality)
        self.jpeg_quality_slider.valueChanged.connect(self._on_jpeg_quality_changed)
        self.jpeg_quality_label = QLabel(str(self.export_settings.jpeg_quality))
        self.jpeg_quality_label.setFixedWidth(36)
        self.jpeg_quality_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        quality_layout.addWidget(self.jpeg_quality_slider)
        quality_layout.addWidget(self.jpeg_quality_label)
        form.addRow("JPEG 质量", quality_container)

        self.scale_mode_combo = QComboBox()
        self.scale_mode_combo.addItems(["不缩放", "按宽度", "按高度", "按百分比"])
        self.scale_mode_combo.currentIndexChanged.connect(self._on_scale_mode_changed)
        form.addRow("尺寸调整", self.scale_mode_combo)

        self.scale_value_spin = QSpinBox()
        self.scale_value_spin.setRange(1, 10000)
        self.scale_value_spin.setValue(max(1, self.export_settings.scale_value))
        self.scale_value_spin.valueChanged.connect(self._on_scale_value_changed)
        self.scale_value_spin.setSingleStep(50)
        form.addRow("目标值", self.scale_value_spin)

        self.export_current_button = QPushButton("导出当前图片")
        self.export_current_button.clicked.connect(self._export_current)
        form.addRow("导出当前", self.export_current_button)

        return group

    def _prompt_import_images(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if files:
            self._add_images([Path(f) for f in files])

    def _prompt_import_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder:
            return
        folder_path = Path(folder)
        files = [p for p in folder_path.iterdir() if p.suffix.lower() in ALLOWED_INPUT_SUFFIXES]
        self._add_images(files)

    def _add_images(self, paths: List[Path]) -> None:
        candidates = image_loader.filter_supported_images(paths)
        if not candidates:
            QMessageBox.information(self, "提示", "未找到可导入的图片文件。")
            return
        new_paths: List[Path] = []
        duplicates: List[Path] = []
        existing = set(self.images)
        for path in candidates:
            if path in existing:
                duplicates.append(path)
            else:
                new_paths.append(path)
                existing.add(path)

        if not new_paths:
            QMessageBox.information(self, "提示", "这些图片已在列表中，无需重复导入。")
            return

        self.images.extend(new_paths)
        self.image_list.populate(self.images, selected=self.current_image)
        if not self.current_image and self.images:
            self.image_list.setCurrentRow(0)

        message = f"成功导入 {len(new_paths)} 张图片。"
        if duplicates:
            message += f"\n已忽略 {len(duplicates)} 张重复图片。"
        QMessageBox.information(self, "完成", message)
        self._update_export_buttons()

    def _remove_images(self, paths: List[Path]) -> None:
        to_remove = [p for p in paths if p in self.images]
        if not to_remove:
            return
        for path in to_remove:
            self.images.remove(path)
            if self.current_image == path:
                self.current_image = None

        if not self.images:
            self.image_list.clear()
            self.preview.clear()
            QMessageBox.information(self, "完成", "所有图片已被移除。")
            self._update_export_buttons()
            return

        next_selection = self.current_image if self.current_image in self.images else self.images[0]
        self.image_list.populate(self.images, selected=next_selection)
        if next_selection in self.images:
            index = self.images.index(next_selection)
            self.image_list.setCurrentRow(index)
            self.current_image = next_selection
        else:
            self.current_image = None
        QMessageBox.information(self, "完成", f"已删除 {len(to_remove)} 张图片。")
        self._update_export_buttons()

    def _update_export_buttons(self) -> None:
        has_images = bool(self.images)
        self.batch_export_button.setEnabled(has_images)
        self.export_toolbar_button.setEnabled(has_images)
        self.export_current_button.setEnabled(has_images and self.current_image is not None)

    def _handle_list_selection(self) -> None:
        items = self.image_list.selectedItems()
        if not items:
            self.current_image = None
            self.preview.clear()
            self._update_export_buttons()
            return
        item: QListWidgetItem = items[0]
        path: Path = item.data(Qt.ItemDataRole.UserRole)
        self.current_image = path
        image = image_loader.load_qimage(path)
        if image.isNull():
            QMessageBox.warning(self, "错误", f"无法加载图片：{path}")
            return
        self.preview.set_image(image)
        self.preview.apply_settings(self.watermark_settings)
        self._update_export_buttons()

    def _on_text_changed(self) -> None:
        self.watermark_settings.text = self.text_edit.toPlainText()
        self.preview.apply_settings(self.watermark_settings)

    def _on_opacity_changed(self, value: int) -> None:
        self.watermark_settings.opacity = value
        self.preview.apply_settings(self.watermark_settings)

    def _on_font_size_changed(self, value: int) -> None:
        self.watermark_settings.font_size = value
        self.preview.apply_settings(self.watermark_settings)

    def _apply_position(self, ratio: QPointF) -> None:
        self.watermark_settings.position_ratio = ratio
        self.preview.apply_settings(self.watermark_settings)

    def _choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if not directory:
            return
        path = Path(directory)
        if any(path == img.parent for img in self.images):
            QMessageBox.warning(self, "提示", "为避免覆盖原图，请选择不同的输出目录。")
            return
        self.export_settings.output_dir = path
        self.output_dir_edit.setText(str(path))

    def _update_naming_mode(self) -> None:
        if self.naming_original.isChecked():
            self.export_settings.naming_mode = "original"
        elif self.naming_prefix.isChecked():
            self.export_settings.naming_mode = "prefix"
        else:
            self.export_settings.naming_mode = "suffix"
        self.prefix_edit.setEnabled(self.export_settings.naming_mode == "prefix")
        self.suffix_edit.setEnabled(self.export_settings.naming_mode == "suffix")

    def _update_output_format(self) -> None:
        index = self.format_combo.currentIndex()
        self.export_settings.output_format = ["auto", "jpeg", "png"][index]
        self._update_quality_controls()

    def _on_jpeg_quality_changed(self, value: int) -> None:
        value = max(0, min(100, value))
        self.jpeg_quality_label.setText(str(value))
        self.export_settings.jpeg_quality = value

    def _set_jpeg_quality(self, value: int) -> None:
        clamped = max(0, min(100, value))
        self.jpeg_quality_slider.blockSignals(True)
        self.jpeg_quality_slider.setValue(clamped)
        self.jpeg_quality_slider.blockSignals(False)
        self.jpeg_quality_label.setText(str(clamped))

    def _update_quality_controls(self) -> None:
        if not hasattr(self, "jpeg_quality_slider"):
            return
        is_jpeg = self.export_settings.output_format == "jpeg"
        self.jpeg_quality_slider.setEnabled(is_jpeg)
        self.jpeg_quality_label.setEnabled(is_jpeg)
        self.jpeg_quality_label.setText(str(self.jpeg_quality_slider.value()))

    def _on_scale_mode_changed(self, index: int) -> None:
        mode = ["none", "width", "height", "percent"][index]
        self.export_settings.scale_mode = mode
        self._refresh_scale_value_constraints()

    def _on_scale_value_changed(self, value: int) -> None:
        if self.export_settings.scale_mode == "none":
            return
        self.export_settings.scale_value = max(1, value)

    def _update_scale_controls(self) -> None:
        if not hasattr(self, "scale_mode_combo"):
            return
        mode_index = {"none": 0, "width": 1, "height": 2, "percent": 3}
        self.scale_mode_combo.blockSignals(True)
        self.scale_mode_combo.setCurrentIndex(mode_index.get(self.export_settings.scale_mode, 0))
        self.scale_mode_combo.blockSignals(False)
        self._refresh_scale_value_constraints()

    def _refresh_scale_value_constraints(self) -> None:
        if not hasattr(self, "scale_value_spin"):
            return
        mode = self.export_settings.scale_mode
        spin = self.scale_value_spin

        if mode == "none":
            spin.blockSignals(True)
            spin.setEnabled(False)
            spin.setSuffix("")
            spin.blockSignals(False)
            return

        spin.blockSignals(True)
        spin.setEnabled(True)
        if mode == "percent":
            spin.setRange(1, 400)
            spin.setSuffix(" %")
            spin.setSingleStep(5)
            value = self.export_settings.scale_value
            if value <= 0:
                value = 100
            value = max(1, min(400, value))
            self.export_settings.scale_value = value
        else:
            spin.setRange(1, 10000)
            spin.setSuffix(" px")
            spin.setSingleStep(50)
            value = self.export_settings.scale_value
            if value <= 0:
                value = 1920 if mode == "width" else 1080
            value = max(1, min(10000, value))
            self.export_settings.scale_value = value
        spin.setValue(self.export_settings.scale_value)
        spin.blockSignals(False)

    def _on_preview_position_changed(self, ratio: QPointF) -> None:
        self.watermark_settings.position_ratio = ratio

    def _refresh_template_list(self) -> None:
        current = self.template_combo.currentText()
        self.template_combo.blockSignals(True)
        self.template_combo.clear()
        self.template_combo.addItem("")
        for name in self.template_manager.list_templates():
            self.template_combo.addItem(name)
        if current:
            idx = self.template_combo.findText(current)
            if idx >= 0:
                self.template_combo.setCurrentIndex(idx)
        self.template_combo.blockSignals(False)

    def _save_template(self) -> None:
        name, ok = QInputDialog.getText(self, "保存模板", "模板名称：")
        if not ok or not name:
            return
        self._sync_export_fields()
        self.template_manager.save_template(name, self.watermark_settings, self.export_settings)
        self._refresh_template_list()
        QMessageBox.information(self, "成功", "模板已保存。")

    def _rename_template(self) -> None:
        current = self.template_combo.currentText()
        if not current:
            QMessageBox.information(self, "提示", "请选择需要重命名的模板。")
            return
        new_name, ok = QInputDialog.getText(self, "重命名模板", "新的名称：", text=current)
        if not ok or not new_name:
            return
        if not self.template_manager.rename_template(current, new_name):
            QMessageBox.warning(self, "失败", "重命名失败，目标名称可能已存在。")
            return
        self._refresh_template_list()
        QMessageBox.information(self, "成功", "模板已重命名。")

    def _delete_template(self) -> None:
        current = self.template_combo.currentText()
        if not current:
            QMessageBox.information(self, "提示", "请选择要删除的模板。")
            return
        confirm = QMessageBox.question(self, "确认", f"确定要删除模板“{current}”吗？")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.template_manager.delete_template(current)
        self._refresh_template_list()
        QMessageBox.information(self, "成功", "模板已删除。")

    def _load_template(self, name: str) -> None:
        if not name:
            return
        data = self.template_manager.load_template(name)
        if not data:
            return
        self.watermark_settings = WatermarkSettings.from_dict(data.get("watermark"))
        self.export_settings = ExportSettings.from_dict(data.get("export"))
        self._apply_settings_to_ui()
        self._update_export_buttons()
        if self.current_image:
            image = image_loader.load_qimage(self.current_image)
            if not image.isNull():
                self.preview.set_image(image)
                self.preview.apply_settings(self.watermark_settings)

    def _sync_export_fields(self) -> None:
        self.export_settings.prefix = self.prefix_edit.text()
        self.export_settings.suffix = self.suffix_edit.text()
        if self.naming_original.isChecked():
            self.export_settings.naming_mode = "original"
        elif self.naming_prefix.isChecked():
            self.export_settings.naming_mode = "prefix"
        else:
            self.export_settings.naming_mode = "suffix"
        self.export_settings.output_format = ["auto", "jpeg", "png"][self.format_combo.currentIndex()]
        self.export_settings.jpeg_quality = self.jpeg_quality_slider.value()
        mode = ["none", "width", "height", "percent"][self.scale_mode_combo.currentIndex()]
        self.export_settings.scale_mode = mode
        if mode != "none":
            self.export_settings.scale_value = self.scale_value_spin.value()

    def _export_current(self) -> None:
        if not self.current_image:
            QMessageBox.information(self, "提示", "请先选择要导出的图片")
            return
        if not self.export_settings.output_dir:
            QMessageBox.warning(self, "提示", "请先指定输出目录")
            return
        if self.export_settings.output_dir == self.current_image.parent:
            QMessageBox.warning(self, "提示", "输出目录不能与原图目录相同")
            return

        self._sync_export_fields()
        try:
            self._export_single(self.current_image)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "失败", f"导出失败：{exc}")
            return

        QMessageBox.information(self, "成功", f"已导出 {self.current_image.name}。")

    def _export_all(self) -> None:
        if not self.images:
            QMessageBox.information(self, "提示", "请先导入图片")
            return
        if not self.export_settings.output_dir:
            QMessageBox.warning(self, "提示", "请先指定输出目录")
            return
        source_dirs = {path.parent for path in self.images}
        if self.export_settings.output_dir in source_dirs:
            QMessageBox.warning(self, "提示", "输出目录不能与原图目录相同")
            return

        self._sync_export_fields()
        errors: List[str] = []
        for path in self.images:
            try:
                self._export_single(path)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{path.name}: {exc}")
        if errors:
            text = "\n".join(errors[:10]) + ("\n…" if len(errors) > 10 else "")
            QMessageBox.warning(self, "部分失败", text)
        else:
            QMessageBox.information(self, "成功", "导出完成！")

    def _export_single(self, path: Path) -> None:
        image = Image.open(path)
        scaled = scale_image(image, self.export_settings)
        composed = compose_watermark(scaled, self.watermark_settings)
        output_dir = self.export_settings.output_dir or path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        target = compute_output_path(path, self.export_settings, output_dir)
        if target.suffix.lower() in {".jpg", ".jpeg"}:
            composed = composed.convert("RGB")
            composed.save(target, quality=self.export_settings.jpeg_quality)
        else:
            composed.save(target)

    def _restore_last_session(self) -> None:
        data = self.template_manager.load_last_session()
        if not data:
            return
        self.watermark_settings = WatermarkSettings.from_dict(data.get("watermark"))
        self.export_settings = ExportSettings.from_dict(data.get("export"))
        image_paths = [Path(p) for p in data.get("images", []) if Path(p).exists()]
        if image_paths:
            self.images = image_paths
            self.image_list.populate(self.images)
            self.image_list.setCurrentRow(0)
            self.current_image = self.images[0]
        self._apply_settings_to_ui()
        self._update_export_buttons()

    def _apply_settings_to_ui(self) -> None:
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(self.watermark_settings.text)
        self.text_edit.blockSignals(False)

        self.opacity_slider.blockSignals(True)
        self.opacity_spin.blockSignals(True)
        self.opacity_slider.setValue(self.watermark_settings.opacity)
        self.opacity_spin.setValue(self.watermark_settings.opacity)
        self.opacity_slider.blockSignals(False)
        self.opacity_spin.blockSignals(False)

        self.font_size_spin.blockSignals(True)
        self.font_size_spin.setValue(self.watermark_settings.font_size)
        self.font_size_spin.blockSignals(False)

        if self.export_settings.output_dir:
            self.output_dir_edit.setText(str(self.export_settings.output_dir))
        else:
            self.output_dir_edit.clear()

        self.prefix_edit.setText(self.export_settings.prefix)
        self.suffix_edit.setText(self.export_settings.suffix)

        mode = self.export_settings.naming_mode
        self.naming_original.setChecked(mode == "original")
        self.naming_prefix.setChecked(mode == "prefix")
        self.naming_suffix.setChecked(mode == "suffix")
        self.prefix_edit.setEnabled(mode == "prefix")
        self.suffix_edit.setEnabled(mode == "suffix")

        index = {"auto": 0, "jpeg": 1, "png": 2}.get(self.export_settings.output_format, 0)
        self.format_combo.setCurrentIndex(index)
        self._set_jpeg_quality(self.export_settings.jpeg_quality)
        self._update_quality_controls()
        self._update_scale_controls()
        self._update_export_buttons()

    def closeEvent(self, event) -> None:
        data = {
            "watermark": self.watermark_settings.to_dict(),
            "export": self.export_settings.to_dict(),
            "images": [str(p) for p in self.images],
        }
        self.template_manager.save_last_session(data)
        super().closeEvent(event)
