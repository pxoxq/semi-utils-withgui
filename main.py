import logging
from pathlib import Path
from tkinter import StringVar, Tk, Label, Button, Entry
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showerror, showinfo
from tkinter.ttk import Progressbar
from os import makedirs
from os.path import exists
# from tqdm import tqdm

from entity.image_container import ImageContainer
from entity.image_processor import ProcessorChain
from enums.constant import DEBUG
from init import MARGIN_PROCESSOR
from init import PADDING_TO_ORIGINAL_RATIO_PROCESSOR
from init import SHADOW_PROCESSOR
from init import SIMPLE_PROCESSOR
from init import config
from init import layout_items_dict
# from init import root_menu
from utils import ENCODING
from utils import get_file_list

# state = 0

# current_menu = root_menu
# root_menu.set_parent(root_menu)

class PhotoMarker:

    def __init__(self):
        self.__root = Tk()
        self.__root.title("图片水印")
        self.__root.geometry("600x200")
        self.start_btn = Button(self.__root, text="开 始", bg='pink', fg='white', font=30, command=self.__start_make, width=40)

        self.progress_bar = Progressbar(self.__root, length=400)
        self.input_dir = StringVar(value="./input")
        self.out_dir = StringVar(value="./output")
        self.current_img_name = StringVar()
        self.current_info_box = Entry(self.__root, state='readonly', textvariable=self.current_img_name)

        self.__init_table()
        self.__root.mainloop()

    def __init_table(self):
        row_index = 1
        input_dir_label = Label(self.__root, text="* 图片目录", font=36)
        input_dir_label.grid(row=row_index, sticky='W', padx=(18, 0), pady=(16, 0))
        row_index += 1
        input_dir_entry = Entry(self.__root, textvariable=self.input_dir, state='readonly', width=77)
        input_dir_entry.grid(row=row_index, column=0, columnspan=4, padx=(20, 0))
        input_dir_btn = Button(self.__root, text="...", command=self.__get_input_dir)
        input_dir_btn.grid(row=row_index, column=5, columnspan=1)
        row_index += 1

        output_dir_label = Label(self.__root, text="* 输出路径", font=36)
        output_dir_label.grid(row=row_index, sticky='W', padx=(18, 0), pady=(16, 0))
        row_index += 1
        output_dir_entry = Entry(self.__root, textvariable=self.out_dir, state='readonly', width=77)
        output_dir_entry.grid(row=row_index, column=0, columnspan=4, padx=(20, 0))
        output_dir_btn = Button(self.__root, text="...", command=self.__get_output_dir)
        output_dir_btn.grid(row=row_index, column=5, columnspan=1)
        row_index += 1

        self.start_btn.grid(row=row_index, columnspan=6, sticky='WE', pady=13, padx=60)

    def __get_output_dir(self):
        output_path = askdirectory(title="选择输出目录")
        output_path and self.out_dir.set(output_path)

    def __get_input_dir(self):
        input_path = askdirectory(title="选择图片目录")
        if input_path:
            self.input_dir.set(input_path)
            self.out_dir.set(input_path + '/with_logo')

    def __check_data(self):
        if not self.input_dir.get():
            showerror("错误", "输入目录不能为空")
            return False
        if not self.out_dir.get():
            showerror("错误", "输出目录不能为空")
            return False
        return True

    def __set_progress_max(self, value: int):
        self.progress_bar['maximum'] = value

    def _update_progress(self, current_val: int, flush: bool = True):
        self.progress_bar['value'] = current_val
        flush and self.__root.update()

    def _toggle_progressbar(self, show: bool = True):
        if show:
            self.progress_bar.grid(columnspan=6, sticky='WE', padx=30, pady=10)
            self.current_info_box.grid(columnspan=6, sticky='WE', padx=30)
            self.__root.geometry("600x215")
            self.start_btn.grid_forget()
        else:
            self.current_info_box.grid_forget()
            self.progress_bar.grid_forget()
            self.__root.geometry("600x200")
            self.start_btn.grid(columnspan=6, sticky='WE', pady=13, padx=60)

    def __start_make(self):
        if not self.__check_data():
            return
        if not exists(self.out_dir.get()):
            makedirs(self.out_dir.get())
        file_list = get_file_list(self.input_dir.get())
        total_files = len(file_list)
        # print('当前共有 {} 张图片待处理'.format(total_files))
        if not total_files:
            showinfo('提示', '文件夹下无JPG文件')
            return

        # 初始化UI进度条
        self.__set_progress_max(total_files)
        self._update_progress(0, False)

        processor_chain = ProcessorChain()

        # 如果需要添加阴影，则添加阴影处理器，阴影处理器优先级最高，但是正方形布局不需要阴影
        if config.has_shadow_enabled() and 'square' != config.get_layout_type():
            processor_chain.add(SHADOW_PROCESSOR)

        # 根据布局添加不同的水印处理器
        if config.get_layout_type() in layout_items_dict:
            processor_chain.add(layout_items_dict.get(config.get_layout_type()).processor)
        else:
            processor_chain.add(SIMPLE_PROCESSOR)

        # 如果需要添加白边，且是水印布局，则添加白边处理器，白边处理器优先级最低
        if config.has_white_margin_enabled() and 'watermark' in config.get_layout_type():
            processor_chain.add(MARGIN_PROCESSOR)

        # 如果需要按原有比例填充，且不是正方形布局，则添加填充处理器
        if config.has_padding_with_original_ratio_enabled() and 'square' != config.get_layout_type():
            processor_chain.add(PADDING_TO_ORIGINAL_RATIO_PROCESSOR)

        # 放置进度条、信息提示
        self._toggle_progressbar()
        self._update_progress(0)

        for idx, source_path in enumerate(file_list, 1):
            self.current_img_name.set(f'  [{idx}/{total_files}] | 当前：{source_path.name}')
            # 打开图片
            container = ImageContainer(source_path)
            # 使用等效焦距
            container.is_use_equivalent_focal_length(config.use_equivalent_focal_length())
            # 处理图片
            try:
                processor_chain.process(container)
            except Exception as e:
                logging.exception(f'Error: {str(e)}')
                if DEBUG:
                    raise e
            # 保存图片
            target_path = Path(self.out_dir.get(), encoding=ENCODING).joinpath(source_path.name)
            container.save(target_path, quality=config.get_quality())
            container.close()
            # 更新进度条、刷新面板
            self._update_progress(idx)

        showinfo('完成', f'处理完成。共 {total_files} 章图片，输出于： {self.out_dir.get()} 目录。')
        # 隐藏进度条、提示信息
        self._toggle_progressbar(False)


if __name__ == '__main__':
    pm = PhotoMarker()
