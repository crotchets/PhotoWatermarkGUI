"""Image preview widget with draggable watermark."""
from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsScene, QGraphicsView

from ..models import WatermarkSettings


class DraggableWatermarkItem(QGraphicsObject):
    """Custom drawable watermark item supporting styles."""

    def __init__(self, on_position_changed, parent=None) -> None:
        super().__init__(parent)
        self._callback = on_position_changed
        self._path = QPainterPath()
        self._rect = QRectF(0, 0, 1, 1)
        self._color = QColor(255, 255, 255, 180)
        self._shadow = False
        self._outline = False
        self._shadow_offset = 2.0
        self._outline_width = 1.5
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def boundingRect(self) -> QRectF:  # noqa: D401
        margin = max(self._shadow_offset if self._shadow else 0.0, self._outline_width if self._outline else 0.0)
        return self._rect.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: D401
        if self._path.isEmpty():
            return
        painter.save()
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        if self._shadow:
            shadow_color = QColor(0, 0, 0, int(self._color.alpha() * 0.6))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(shadow_color)
            painter.drawPath(self._path.translated(self._shadow_offset, self._shadow_offset))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)
        painter.drawPath(self._path)

        if self._outline:
            outline_color = QColor(0, 0, 0, self._color.alpha())
            pen = QPen(outline_color, self._outline_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._path)
        painter.restore()

    def update_settings(self, settings: WatermarkSettings) -> None:
        font = QFont(settings.font_family or "Arial", pointSize=settings.font_size)
        font.setBold(settings.bold)
        font.setItalic(settings.italic)

        metrics = QFontMetrics(font)
        lines = settings.text.splitlines() or [""]
        path = QPainterPath()
        y = 0
        for line in lines:
            content = line or " "
            path.addText(0, y + metrics.ascent(), font, content)
            y += metrics.lineSpacing()
        if path.isEmpty():
            path.addText(0, metrics.ascent(), font, " ")

        rect = path.boundingRect()
        if rect.x() or rect.y():
            path.translate(-rect.x(), -rect.y())
            rect = path.boundingRect()

        self.prepareGeometryChange()
        self._path = path
        self._rect = rect
        alpha = int(255 * (settings.opacity / 100))
        self._color = QColor(settings.color or "#FFFFFF")
        self._color.setAlpha(alpha)
        self._shadow = settings.shadow
        self._outline = settings.outline
        self._shadow_offset = max(2.0, font.pointSizeF() * 0.08)
        self._outline_width = max(1.5, font.pointSizeF() * 0.1)
        self.setTransformOriginPoint(self._rect.center())
        self.setRotation(-settings.rotation)
        self.update()

    def content_size(self) -> QPointF:
        return QPointF(self._rect.width(), self._rect.height())

    def itemChange(self, change, value):  # noqa: D401
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged and self._callback:
            self._callback(self.pos())
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
        self._watermark_item = DraggableWatermarkItem(self._on_position_changed)
        self._on_ratio_changed = on_position_ratio_changed

    def clear(self) -> None:
        self.scene().clear()
        self._pixmap_item = None
        self._image_size = None
        self._watermark_item = DraggableWatermarkItem(self._on_position_changed)

    def set_image(self, image) -> None:
        self.clear()
        pixmap = QPixmap.fromImage(image)
        self._pixmap_item = self.scene().addPixmap(pixmap)
        self._image_size = image.size()
        self.scene().addItem(self._watermark_item)
        self._watermark_item.setZValue(1)
        self._center_view()

    def apply_settings(self, settings: WatermarkSettings) -> None:
        self._watermark_item.update_settings(settings)
        self._set_position_ratio(settings.position_ratio)

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
        size = self._watermark_item.content_size()
        x = ratio.x() * max(1, self._image_size.width() - size.x())
        y = ratio.y() * max(1, self._image_size.height() - size.y())
        self._watermark_item.setPos(x, y)

    def _on_position_changed(self, pos) -> None:
        if not self._image_size:
            return
        size = self._watermark_item.content_size()
        width = max(1, self._image_size.width() - size.x())
        height = max(1, self._image_size.height() - size.y())
        ratio = QPointF(pos.x() / width, pos.y() / height)
        ratio.setX(min(max(ratio.x(), 0.0), 1.0))
        ratio.setY(min(max(ratio.y(), 0.0), 1.0))
        if self._on_ratio_changed:
            self._on_ratio_changed(ratio)

    def set_zoom_fit(self) -> None:
        self._center_view()
