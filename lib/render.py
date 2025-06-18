from copy import copy

from PIL import Image
from PIL.Image import Transpose, Resampling

from lib.data import CursorProject, ProcessStep, Margins, Scale2D, ReverseWay
from lib.log import logger
from lib.perf import Counter

NONE_MARGINS = Margins(0, 0, 0, 0)
NONE_SCALE = Scale2D(1.0, 1.0)


def render_project(project: CursorProject) -> list[Image.Image]:
    if not project.is_ani_cursor:
        return [render_project_frame(project, 0)]
    frames = []
    for frame in range(project.frame_count):
        frames.append(render_project_frame(project, frame))
    return frames


def render_project_gen(project: CursorProject):
    if not project.is_ani_cursor:
        yield render_project_frame(project, 0)
        return
    for frame in range(project.frame_count):
        yield render_project_frame(project, frame)


def render_project_frame(project: CursorProject, frame: int) -> Image.Image:
    timer = Counter(create_start=True)
    canvas = Image.new("RGBA", project.raw_canvas_size, (255, 255, 255, 0))
    for element in project.elements[::-1]:
        element_frames = len(element.frames)
        if element_frames == 1:
            frame_index = 0
        else:
            if frame < element.animation_start_offset:
                continue
            frame_index = element.get_frame_index(frame) % (element_frames - 1)

        item = element.frames[frame_index]
        left_step = copy(list(element.proc_step))
        x_off = y_off = 0
        while len(left_step) != 0:
            step = left_step.pop(0)
            if step == ProcessStep.TRANSPOSE and (element.reverse_x or element.reverse_y):
                if element.reverse_way == ReverseWay.BOTH and element.reverse_x and element.reverse_y:
                    item = item.transpose(Transpose.TRANSPOSE)
                    continue
                if element.reverse_way != ReverseWay.Y_FIRST and element.reverse_x:
                    item = item.transpose(Transpose.FLIP_LEFT_RIGHT)
                    if element.reverse_y:
                        item = item.transpose(Transpose.FLIP_TOP_BOTTOM)
                if element.reverse_way != ReverseWay.X_FIRST and element.reverse_y:
                    item = item.transpose(Transpose.FLIP_TOP_BOTTOM)
                    if element.reverse_x:
                        item = item.transpose(Transpose.FLIP_LEFT_RIGHT)

            elif step == ProcessStep.CROP and element.crop_margins != NONE_MARGINS:
                mrg = element.crop_margins
                item = item.crop((0 + mrg.left, 0 + mrg.up, item.width - mrg.right, item.height - mrg.down))

            elif step == ProcessStep.SCALE and element.scale != NONE_SCALE:
                item = item.resize((int(item.width * element.scale[0]),
                                    int(item.height * element.scale[1])),
                                   element.resample)

            elif step == ProcessStep.ROTATE and element.rotation != 0:
                size = item.size
                rotate_resample = element.resample
                if rotate_resample not in (Resampling.NEAREST, Resampling.BILINEAR, Resampling.BICUBIC):
                    rotate_resample = Resampling.NEAREST
                item = item.rotate(element.rotation, rotate_resample, expand=True, center=(size[0] // 2, size[1] // 2))
                if element.rotation % 90 == 0:
                    x_off = y_off = 0
                else:
                    x_off, y_off = (item.width - size[0]) // 2, (item.height - size[1]) // 2

        element.final_rect = (element.position[0] - x_off, element.position[1] - y_off, item.width, item.height)
        element.final_image = item
        mask = element.mask if element.mask and element.mask.size == item.size else item.getchannel("A")
        canvas.paste(item, (element.position[0] - x_off, element.position[1] - y_off), mask)
    scaled_canvas = canvas.resize(project.canvas_size, project.resample)
    logger.debug(f"渲染第{str(frame).zfill(2)}帧耗时: {timer.endT()}")
    return scaled_canvas
