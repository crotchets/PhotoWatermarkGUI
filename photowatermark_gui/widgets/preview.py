"""Image preview widget with draggable watermark."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsTextItem, QGraphicsView

from ..models import WatermarkSettings


class DraggableTextItem(QGraphicsTextItem):
    """Watermark text item that notifies on position change."""

    def __init__(self, on_position_changed, parent=None) -> None:
        super().__init__(parent)
        self._callback = on_position_changed
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):  # noqa: D401
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self._callback:
            self._callback(self.scenePos())
        return super().itemChange(change, value)


class ImagePreview(QGraphicsView):
    """Shows the current image with live watermark preview."""

    def __init__(self, on_position_ratio_changed, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
            | QPainter.RenderHint.TextAntialiasing
        )
        self.setBackgroundBrush(QBrush(QColor("#202020")))
        self._pixmap_item = None
        self._image_size = None
        self._watermark_item = DraggableTextItem(self._on_position_changed)
        self.scene().addItem(self._watermark_item)
        self._on_ratio_changed = on_position_ratio_changed

    def clear(self) -> None:
        self.scene().clear()
        self._pixmap_item = None
        self._image_size = None
        self._watermark_item = DraggableTextItem(self._on_position_changed)
        self.scene().addItem(self._watermark_item)

    def set_image(self, image: QImage) -> None:
        self.clear()
        pixmap = QPixmap.fromImage(image)
        self._pixmap_item = self.scene().addPixmap(pixmap)
        self._image_size = image.size()
        self._center_view()

    def apply_settings(self, settings: WatermarkSettings) -> None:
        self._watermark_item.setPlainText(settings.text or " ")
        font = QFont()
        font.setPointSize(settings.font_size)
        self._watermark_item.setFont(font)
        color = QColor(255, 255, 255, int(255 * (settings.opacity / 100)))
        self._watermark_item.setDefaultTextColor(color)
        self._set_position_ratio(settings.position_ratio)
        self._watermark_item.setRotation(-settings.rotation)

    def _center_view(self) -> None:
        if not self._pixmap_item:
            return
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_view()

    def _set_position_ratio(self, ratio: QPointF) -> None:
        if not self._image_size:
            return
        text_rect = self._watermark_item.boundingRect()
        x = ratio.x() * max(1, self._image_size.width() - text_rect.width())
        y = ratio.y() * max(1, self._image_size.height() - text_rect.height())
        self._watermark_item.setPos(x, y)

    def _on_position_changed(self, pos) -> None:
        if not self._image_size:
            return
        text_rect = self._watermark_item.boundingRect()
        width = max(1, self._image_size.width() - text_rect.width())
        height = max(1, self._image_size.height() - text_rect.height())
        ratio = QPointF(pos.x() / width, pos.y() / height)
        ratio.setX(min(max(ratio.x(), 0.0), 1.0))
        ratio.setY(min(max(ratio.y(), 0.0), 1.0))
        if self._on_ratio_changed:
            self._on_ratio_changed(ratio)

    def set_zoom_fit(self) -> None:
        self._center_view()
