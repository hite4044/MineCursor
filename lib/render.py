from PIL import Image
from PIL.Image import Transpose, Resampling

from lib.data import CursorProject


def render_project(project: CursorProject) -> list[Image.Image]:
    if project.frame_count == -1:
        return [render_project_frame(project, 0)]
    frames = []
    for frame in range(project.frame_count):
        frames.append(render_project_frame(project, frame))
    return frames


def render_project_frame(project: CursorProject, frame: int) -> Image.Image:
    canvas = Image.new("RGBA", project.raw_canvas_size, (255, 255, 255, 0))
    for element in project.elements[::-1]:
        if len(element.frames) == 1:
            frame_index = 0
        else:
            frame_index = frame % element.animation_length + element.animation_start
            frame_index = max(0, min(frame_index, len(element.frames) - 1))
        item = element.frames[frame_index]
        if element.reverse_x and element.reverse_y:
            item = item.transpose(Transpose.TRANSPOSE)
        elif element.reverse_x:
            item = item.transpose(Transpose.FLIP_LEFT_RIGHT)
        elif element.reverse_y:
            item = item.transpose(Transpose.FLIP_TOP_BOTTOM)

        mrg = element.crop_margins
        item = item.crop((0 + mrg.left, 0 + mrg.up, item.width - mrg.right, item.height - mrg.down))

        item = item.resize((int(item.width * element.scale[0]),
                            int(item.height * element.scale[1])),
                           element.resample)
        size = item.size

        rotate_resample = element.resample
        if rotate_resample not in (Resampling.NEAREST, Resampling.BILINEAR, Resampling.BICUBIC):
            rotate_resample = Resampling.NEAREST
        item = item.rotate(element.rotation, rotate_resample, expand=True)
        x_off, y_off = (item.width - item.width) // 2, (item.height - item.height) // 2

        element.final_rect = (element.position[0] + x_off, element.position[1] + y_off, size[0], size[1])
        canvas.paste(item, (element.position[0] + x_off, element.position[1] + y_off), item.getchannel("A"))
    return canvas.resize(project.canvas_size, project.resample)
