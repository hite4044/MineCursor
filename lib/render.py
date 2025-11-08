from copy import copy

from PIL import Image
from PIL.Image import Transpose, Resampling

from lib.data import CursorProject, ProcessStep, Margins, Scale2D, ReverseWay
from lib.log import logger
from lib.perf import Counter

NONE_MARGINS = Margins(0, 0, 0, 0)
NONE_SCALE = Scale2D(1.0, 1.0)


def render_project(project: CursorProject, for_export=False) -> list[Image.Image]:
    if not project.is_ani_cursor:
        return [render_project_frame(project, 0, for_export)]
    frames = []
    for frame in range(project.frame_count):
        frames.append(render_project_frame(project, frame, for_export))
    return frames


def render_project_gen(project: CursorProject, for_export=False):
    if not project.is_ani_cursor:
        yield render_project_frame(project, 0, for_export)
        return
    for frame in range(project.frame_count):
        yield render_project_frame(project, frame, for_export)


def render_project_frame(project: CursorProject, frame: int, for_export=False) -> Image.Image:
    timer = Counter(create_start=True)
    canvas = Image.new("RGBA", project.raw_canvas_size, (255, 255, 255, 0))
    cnt = 0
    for element in project.elements[::-1]:
        # 提取元素帧
        if element.sub_project:
            if element.sub_project.is_ani_cursor and element.sub_project.frame_count != 0:
                element_frames = element.sub_project.frame_count
            else:
                element_frames = 1
        else:
            element_frames = len(element.frames)
        if frame < element.animation_start_offset:
            continue
        if not element.loop_animation and frame - element.animation_start_offset >= element_frames:
            continue

        if element_frames == 1:
            frame_index = 0
            item = element.frames[frame_index]
        else:
            if element.sub_project:
                sub_project = element.sub_project
                frame_index = frame - element.animation_start_offset
                if element.sub_project.is_ani_cursor and element.sub_project.frame_count != 0:
                    frame_index %= element.sub_project.frame_count
                if element.reverse_animation:
                    frame_index = element_frames - frame_index - 1
                item = render_project_frame(sub_project, frame_index, False)
            else:
                temp_index = element.get_frame_index(frame)
                frame_index = temp_index % element_frames
                if element.reverse_animation:
                    frame_index = element_frames - frame_index - 1
                item = element.frames[frame_index]

        # 按需填色
        if element.mask_color is not None:
            if hasattr(item, "raw_image"):
                item_mask = item.raw_image
            else:
                item_mask = item.convert("L")
            item = Image.new("RGBA", item.size, element.mask_color + (0,))
            item.putalpha(item_mask)

        # 按顺序进行操作
        left_step = copy(list(element.proc_step))
        x_off = y_off = 0
        oper_cnt = 0
        while len(left_step) != 0:
            step = left_step.pop(0)
            if step == ProcessStep.TRANSPOSE and (element.reverse_x or element.reverse_y):
                oper_cnt += 1
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
                oper_cnt += 1
                mrg = element.crop_margins
                item = item.crop((0 + mrg.left, 0 + mrg.up, item.width - mrg.right, item.height - mrg.down))

            elif step == ProcessStep.SCALE and element.scale != NONE_SCALE:
                oper_cnt += 1
                item = item.resize((int(item.width * element.scale[0]),
                                    int(item.height * element.scale[1])),
                                   element.scale_resample)

            elif step == ProcessStep.ROTATE and element.rotation != 0:
                oper_cnt += 1
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
        element.final_image = item.copy()
        if oper_cnt == 0:
            item = item.copy()
        if element.mask is not None and element.mask.size != item.size and element.allow_mask_scale:
            mask = element.mask.resize(item.size, element.scale_resample)
        else:
            mask = element.mask
        if element.sub_project:
            if mask is not None and mask.size == item.size:
                orig_mask = item.getchannel("A")
                new_mask = Image.new("L", orig_mask.size, 0)
                new_mask.paste(orig_mask, mask)
                item.putalpha(new_mask)
            canvas.alpha_composite(item, (element.position[0] - x_off, element.position[1] - y_off))
        else:
            if mask and mask.size == item.size:
                item.putalpha(mask)
            canvas.alpha_composite(item, (element.position[0] - x_off, element.position[1] - y_off))
        cnt += 1
    scaled_canvas = canvas.resize(project.canvas_size, project.resample)
    if cnt == 0 and for_export:
        scaled_canvas.putalpha(1)
    logger.debug(f"渲染第{str(frame).zfill(2)}帧耗时: {timer.endT()}")
    return scaled_canvas
