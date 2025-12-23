"""Spectrum analyzer visualization widget for GTK4"""

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import math
import cairo


class SpectrumVisualizer(Gtk.DrawingArea):
    """Audio spectrum visualization widget"""

    def __init__(self):
        super().__init__()

        # Spectrum data
        self.magnitudes = []
        self.num_bands = 80  # More bars for denser disco effect
        self.smoothed_magnitudes = [0.0] * self.num_bands

        # Visual settings
        self.bar_spacing = 1  # Tighter spacing for disco look
        self.smoothing_factor = 0.65  # Slightly more responsive
        self.peak_hold = True
        self.peak_values = [0.0] * self.num_bands
        self.peak_decay = 0.92  # Faster decay for more dynamic look

        # Style
        self.style = 'bars'  # bars, line, gradient
        self.show_peaks = True

        # Animation
        self.is_active = False

        # Colors (will be updated from system theme)
        self.fg_color = Gdk.RGBA()
        self.fg_color.parse('#3584e4')  # Default blue

        # Set minimum size
        self.set_size_request(400, 200)

        # Set draw function
        self.set_draw_func(self._on_draw)

        # Update colors from theme
        GLib.idle_add(self._update_colors_from_theme)

    def _update_colors_from_theme(self):
        """Update colors from system theme"""
        try:
            # Try to get accent color from theme
            color = self.get_style_context().get_color()
            if color:
                self.fg_color = color
        except Exception as e:
            print(f"Could not get theme colors: {e}")

    def set_spectrum_data(self, magnitudes):
        """Update spectrum data"""
        if not magnitudes:
            return

        self.magnitudes = magnitudes

        # Ensure we have the right number of bands
        while len(self.magnitudes) < self.num_bands:
            self.magnitudes.append(-80.0)

        self.magnitudes = self.magnitudes[:self.num_bands]

        # Apply smoothing
        for i in range(self.num_bands):
            magnitude = self.magnitudes[i]

            # Convert from dB to normalized value (0-1)
            # Typically magnitudes range from -80 to 0 dB
            normalized = (magnitude + 80) / 80.0
            normalized = max(0.0, min(1.0, normalized))

            # Smooth the value
            self.smoothed_magnitudes[i] = (
                self.smoothing_factor * self.smoothed_magnitudes[i] +
                (1 - self.smoothing_factor) * normalized
            )

            # Update peak hold
            if self.smoothed_magnitudes[i] > self.peak_values[i]:
                self.peak_values[i] = self.smoothed_magnitudes[i]
            else:
                self.peak_values[i] *= self.peak_decay

        # Trigger redraw
        self.queue_draw()

    def set_style(self, style: str):
        """Set visualization style (bars, line, gradient)"""
        if style in ['bars', 'line', 'gradient']:
            self.style = style
            self.queue_draw()

    def set_show_peaks(self, show: bool):
        """Enable/disable peak markers"""
        self.show_peaks = show
        self.queue_draw()

    def set_active(self, active: bool):
        """Activate or deactivate spectrum visualization"""
        self.is_active = active

        if not active:
            # Clear magnitudes when inactive
            self.smoothed_magnitudes = [0.0] * self.num_bands
            self.peak_values = [0.0] * self.num_bands
            self.queue_draw()

    def _on_draw(self, area, cr, width, height):
        """Draw the spectrum visualization"""
        # Clear background
        cr.set_source_rgba(0, 0, 0, 0)  # Transparent
        cr.paint()

        if not self.is_active or not self.smoothed_magnitudes:
            return

        if self.style == 'bars':
            self._draw_bars(cr, width, height)
        elif self.style == 'line':
            self._draw_line(cr, width, height)

    def _draw_bars(self, cr, width, height):
        """Draw bar-style spectrum with disco/rainbow effect"""
        bar_width = (width - (self.num_bands - 1) * self.bar_spacing) / self.num_bands

        for i, magnitude in enumerate(self.smoothed_magnitudes):
            x = i * (bar_width + self.bar_spacing)
            bar_height = magnitude * height

            # Rainbow color based on position (0-360 degrees hue)
            hue = (i / self.num_bands) * 360

            # Convert HSV to RGB for rainbow effect
            # Saturation increases with magnitude for more vibrant colors at higher levels
            saturation = 0.6 + (magnitude * 0.4)  # 60% to 100%
            value = 0.8 + (magnitude * 0.2)  # 80% to 100% brightness

            r, g, b = self._hsv_to_rgb(hue, saturation, value)

            # Draw glow effect (larger, semi-transparent bar behind)
            if magnitude > 0.1:
                glow_width = bar_width + 4
                glow_x = x - 2
                cr.set_source_rgba(r, g, b, 0.3 * magnitude)
                self._draw_rounded_rectangle(cr, glow_x, height - bar_height - 2,
                                            glow_width, bar_height + 2, 3)
                cr.fill()

            # Main bar with higher opacity
            alpha = 0.85 + (magnitude * 0.15)  # 85% to 100% opacity
            cr.set_source_rgba(r, g, b, alpha)
            self._draw_rounded_rectangle(cr, x, height - bar_height,
                                        bar_width, bar_height, 2)
            cr.fill()

            # Bright highlight at the top of each bar
            if bar_height > 5:
                highlight_height = min(bar_height * 0.3, 10)
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.4 * magnitude)
                self._draw_rounded_rectangle(cr, x, height - bar_height,
                                            bar_width, highlight_height, 2)
                cr.fill()

            # Draw peak marker with matching color
            if self.show_peaks and self.peak_values[i] > 0.05:
                peak_y = height - (self.peak_values[i] * height)
                peak_alpha = self.peak_values[i] * 0.9
                cr.set_source_rgba(r, g, b, peak_alpha)
                self._draw_rounded_rectangle(cr, x, peak_y - 3, bar_width, 3, 1.5)
                cr.fill()

    def _hsv_to_rgb(self, h, s, v):
        """Convert HSV color to RGB (h: 0-360, s: 0-1, v: 0-1)"""
        h = h / 60.0
        i = int(h)
        f = h - i

        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))

        i = i % 6

        if i == 0: return v, t, p
        if i == 1: return q, v, p
        if i == 2: return p, v, t
        if i == 3: return p, q, v
        if i == 4: return t, p, v
        if i == 5: return v, p, q

        return 0, 0, 0

    def _draw_rounded_rectangle(self, cr, x, y, width, height, radius):
        """Draw a rounded rectangle"""
        if height < radius * 2:
            radius = height / 2
        if width < radius * 2:
            radius = width / 2

        cr.new_sub_path()
        cr.arc(x + width - radius, y + radius, radius, -90 * (math.pi/180), 0)
        cr.arc(x + width - radius, y + height - radius, radius, 0, 90 * (math.pi/180))
        cr.arc(x + radius, y + height - radius, radius, 90 * (math.pi/180), 180 * (math.pi/180))
        cr.arc(x + radius, y + radius, radius, 180 * (math.pi/180), 270 * (math.pi/180))
        cr.close_path()

    def _draw_line(self, cr, width, height):
        """Draw line-style spectrum with rainbow gradient effect"""
        if not self.smoothed_magnitudes:
            return

        step = width / (self.num_bands - 1)

        # Draw multiple colored segments to create rainbow effect
        for i in range(self.num_bands - 1):
            x1 = i * step
            x2 = (i + 1) * step
            y1 = height - (self.smoothed_magnitudes[i] * height)
            y2 = height - (self.smoothed_magnitudes[i + 1] * height)

            # Rainbow color for this segment
            hue = (i / self.num_bands) * 360
            avg_mag = (self.smoothed_magnitudes[i] + self.smoothed_magnitudes[i + 1]) / 2
            r, g, b = self._hsv_to_rgb(hue, 0.8, 0.9)

            # Draw thick line segment
            cr.set_line_width(3.0)
            cr.set_source_rgba(r, g, b, 0.9)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

            # Draw glow effect
            cr.set_line_width(6.0)
            cr.set_source_rgba(r, g, b, 0.3 * avg_mag)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

        # Draw semi-transparent filled area with rainbow effect
        for i in range(self.num_bands - 1):
            x1 = i * step
            x2 = (i + 1) * step
            y1 = height - (self.smoothed_magnitudes[i] * height)
            y2 = height - (self.smoothed_magnitudes[i + 1] * height)

            hue = (i / self.num_bands) * 360
            r, g, b = self._hsv_to_rgb(hue, 0.6, 0.8)

            # Create filled polygon for this segment
            cr.move_to(x1, height)
            cr.line_to(x1, y1)
            cr.line_to(x2, y2)
            cr.line_to(x2, height)
            cr.close_path()

            cr.set_source_rgba(r, g, b, 0.2)
            cr.fill()

    def reset(self):
        """Reset spectrum to zero"""
        self.smoothed_magnitudes = [0.0] * self.num_bands
        self.peak_values = [0.0] * self.num_bands
        self.magnitudes = []
        self.queue_draw()
