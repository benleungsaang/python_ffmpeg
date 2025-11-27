import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import threading
import time
import subprocess
import queue
from datetime import datetime
from tkinterdnd2 import DND_FILES, TkinterDnD

class VideoTranscoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频转码工具")
        self.root.attributes('-topmost', True)  # 窗口置顶

        # 设置窗口大小
        self.root.geometry("1000x700")

        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 配置主窗口的行和列权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # 1. 视频文件地址输入框
        ttk.Label(main_frame, text="视频文件地址:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.video_file_path = tk.StringVar()
        video_file_frame = ttk.Frame(main_frame)
        video_file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        video_file_frame.columnconfigure(0, weight=1)

        self.video_file_entry = tk.Entry(video_file_frame, textvariable=self.video_file_path)  # 使用普通tk.Entry
        self.video_file_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        # 绑定拖放事件
        self.video_file_entry.drop_target_register(DND_FILES)
        self.video_file_entry.dnd_bind('<<Drop>>', self.on_drop_video)

        ttk.Button(video_file_frame, text="选择文件", command=self.browse_video_file).grid(row=0, column=1)

        # 2. 扫描视频文件夹地址输入框
        ttk.Label(main_frame, text="扫描视频文件夹地址:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.scan_folder_path = tk.StringVar()
        scan_folder_frame = ttk.Frame(main_frame)
        scan_folder_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        scan_folder_frame.columnconfigure(0, weight=1)

        self.scan_folder_entry = ttk.Entry(scan_folder_frame, textvariable=self.scan_folder_path)
        self.scan_folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))

        # 绑定拖放事件 - 支持文件和文件夹
        self.scan_folder_entry.drop_target_register(DND_FILES)
        self.scan_folder_entry.dnd_bind('<<Drop>>', self.on_drop_scan)

        ttk.Button(scan_folder_frame, text="选择文件夹", command=self.browse_scan_folder).grid(row=0, column=1)

        # 3. 扫描按钮和覆盖选项复选框
        scan_controls_frame = ttk.Frame(main_frame)
        scan_controls_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(scan_controls_frame, text="扫描关键字:").pack(side=tk.LEFT, padx=(0, 5))
        self.scan_keyword = tk.StringVar()
        self.scan_keyword.set('unTransCode')
        ttk.Entry(scan_controls_frame, textvariable=self.scan_keyword, width=15).pack( side=tk.LEFT, padx=(0, 10))


        ttk.Label(scan_controls_frame, text="替换为:").pack(side=tk.LEFT, padx=(0, 5))
        self.replace_keyword = tk.StringVar()
        self.replace_keyword.set('Soonwin')
        ttk.Entry(scan_controls_frame, textvariable=self.replace_keyword, width=15).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(scan_controls_frame, text="扫描", command=self.scan_videos).pack(side=tk.LEFT, padx=(0, 10))

        self.overwrite_var = tk.BooleanVar(value=False)  # 默认不选中
        ttk.Checkbutton(scan_controls_frame, text="转码后输出到原目录", variable=self.overwrite_var).pack(side=tk.LEFT)

        # 4. 当前任务进度条
        ttk.Label(main_frame, text="当前任务进度:").grid(row=5, column=0, sticky=tk.W, pady=(10, 2))
        self.current_progress = ttk.Progressbar(main_frame, mode='determinate')
        self.current_progress.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)

        # 5. 任务队列进度条
        ttk.Label(main_frame, text="任务队列进度:").grid(row=7, column=0, sticky=tk.W, pady=(5, 2))
        self.queue_progress = ttk.Progressbar(main_frame, mode='determinate')
        self.queue_progress.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)

        # 6. 任务列表
        ttk.Label(main_frame, text="任务列表:（双击任务删除）").grid(row=9, column=0, sticky=tk.W, pady=(10, 2))

        # 创建任务列表框架
        task_frame = ttk.Frame(main_frame)
        task_frame.grid(row=10, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        task_frame.columnconfigure(0, weight=1)
        task_frame.rowconfigure(0, weight=1)

        # 创建任务列表表格
        columns = ("index", "filename", "original_size", "estimated_size", "transcoded_size", "completed_time", "duration", "operation", "status")
        self.task_tree = ttk.Treeview(task_frame, columns=columns, show="headings", height=8)

        # 定义列标题
        self.task_tree.heading("index", text="序号")
        self.task_tree.heading("filename", text="文件名")
        self.task_tree.heading("original_size", text="原文件大小")
        self.task_tree.heading("estimated_size", text="预估转码大小")
        self.task_tree.heading("transcoded_size", text="转码后大小")
        self.task_tree.heading("completed_time", text="完成时间")
        self.task_tree.heading("duration", text="转码用时")
        self.task_tree.heading("operation", text="执行操作")
        self.task_tree.heading("status", text="转码状态")

        # 设置列宽
        self.task_tree.column("index", width=40, anchor="center")  # 序号列较窄并居中
        self.task_tree.column("filename", width=150)
        self.task_tree.column("original_size", width=80)
        self.task_tree.column("estimated_size", width=90)
        self.task_tree.column("transcoded_size", width=80)
        self.task_tree.column("completed_time", width=120)
        self.task_tree.column("duration", width=80)
        self.task_tree.column("operation", width=100)
        self.task_tree.column("status", width=100)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(task_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.task_tree.configure(yscrollcommand=scrollbar.set)

        # 配置行权重，使任务列表可以扩展
        main_frame.rowconfigure(10, weight=1)

        # 创建右键菜单
        self.task_context_menu = tk.Menu(self.root, tearoff=0)
        self.task_context_menu.add_command(label="打开文件", command=self.open_selected_file)
        self.task_context_menu.add_command(label="打开目录", command=self.open_selected_directory)
        self.task_context_menu.add_separator()
        self.task_context_menu.add_command(label="只改名不转码", command=self.rename_only)
        self.task_context_menu.add_command(label="删除任务", command=self.delete_selected_task)

        # 绑定双击事件用于删除任务
        self.task_tree.bind("<Double-1>", self.on_task_double_click)
        # 绑定右键点击事件
        self.task_tree.bind("<Button-3>", self.show_context_menu)  # Windows/Linux
        self.task_tree.bind("<Button-2>", self.show_context_menu)  # macOS

        # 为整个界面添加拖拽支持
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_general_drop)

        # 任务统计信息标签
        self.stats_label = ttk.Label(main_frame, text="任务统计：共0个任务，待处理0个，已完成0个，失败0个")
        self.stats_label.grid(row=11, column=0, columnspan=2, sticky=tk.W, pady=(5, 5))

        # 7. 任务执行按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=12, column=0, columnspan=2, pady=10)
        button_frame.columnconfigure(0, weight=1)

        # 配置开始按钮宽度为整程序宽度，高度为4行高
        self.task_control_button = ttk.Button(button_frame, text="开始任务", command=self.task_control)
        self.task_control_button.grid(row=0, column=0, sticky=(tk.W, tk.E), ipady=20)  # 增加高度

        bottom_button_frame = ttk.Frame(main_frame)
        bottom_button_frame.grid(row=13, column=0, columnspan=2, pady=5)

        self.estimate_button = ttk.Button(bottom_button_frame, text="计算预估大小", command=self.calculate_all_estimates)
        self.estimate_button.pack(side=tk.LEFT, padx=(0, 10))

        self.config_button = ttk.Button(bottom_button_frame, text="配置转码参数", command=self.open_config_dialog)
        self.config_button.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_button = ttk.Button(bottom_button_frame, text="清空已完成任务", command=self.clear_completed_tasks)
        self.clear_button.pack(side=tk.LEFT)

        # 初始化任务列表
        self.tasks = []
        self.running = False
        self.paused = False

        # 初始化默认转码参数
        self.ffmpeg_params = (
            "-c:v libx264 -profile:v main -level 4.0 "
            "-crf 28 -preset medium "
            "-maxrate 8500000 -bufsize 17000000 "
            '-vf "scale=w=min(iw\\,1920):h=-2:force_original_aspect_ratio=decrease,'
            'pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2:x=0:y=0:color=black,'
            'format=yuv420p" '
            "-c:a aac -ac 2 -ar 44100 -b:a 128000 "
            "-r 30 "
            "-threads 0 -x264-params \"threads=0:sliced-threads=1\" "
            "-f mp4 -movflags +faststart -y"
        )

        # 设置音频码率 - 在初始化时定义
        self.AUDIO_BITRATE = 128000  # 128kbps
        self.MAX_MAXRATE = 8500000  # 8.5Mbps

    def on_drop_video(self, event):
        """处理视频文件拖拽事件"""
        files = self.root.tk.splitlist(event.data)
        if files:
            # 取第一个文件作为输入框显示
            self.video_file_path.set(files[0])
            # 添加所有文件作为任务
            for file_path in files:
                if os.path.isfile(file_path):
                    self.add_task(file_path)

    def on_drop_scan(self, event):
        """处理扫描文件夹拖拽事件"""
        files = self.root.tk.splitlist(event.data)
        if files:
            path = files[0]  # 取第一个文件或文件夹
            if os.path.isdir(path):
                self.scan_folder_path.set(path)
            elif os.path.isfile(path):
                # 如果拖拽的是文件，设置为文件的目录
                self.scan_folder_path.set(os.path.dirname(path))

    def browse_video_file(self):
        """浏览并选择视频文件"""
        filename = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v *.3gp *.mpg *.mpeg *.ts *.m2ts"),
                ("所有文件", "*.*")
            ]
        )
        if filename:
            self.video_file_path.set(filename)
            self.add_task(filename)

    def browse_scan_folder(self):
        """浏览并选择扫描文件夹"""
        foldername = filedialog.askdirectory(title="选择视频文件夹")
        if foldername:
            self.scan_folder_path.set(foldername)

    def scan_videos(self):
        """扫描文件夹中的视频文件"""
        folder_path = self.scan_folder_path.get()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showerror("错误", "请选择有效的文件夹路径")
            return

        # 支持的视频文件扩展名
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg', '.ts', '.m2ts'}

        # 获取扫描关键字
        scan_keyword = self.scan_keyword.get().strip()

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in video_extensions:
                    # 如果设置了扫描关键字，则只添加包含关键字的文件
                    if scan_keyword and scan_keyword not in file:
                        continue

                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        self.add_task(file_path)

    def add_task(self, file_path):
        """添加转码任务到列表"""
        if not os.path.exists(file_path):
            messagebox.showerror("错误", f"文件不存在: {file_path}")
            return

        # 检查是否已存在相同路径的任务
        for task in self.tasks:
            if task['file_path'] == file_path:
                messagebox.showinfo("提示", f"任务已存在: {file_path}")
                return

        file_size = os.path.getsize(file_path)
        task = {
            'id': len(self.tasks),
            'file_path': file_path,
            'filename': os.path.basename(file_path),
            'original_size': self.format_file_size(file_size),
            'estimated_size': '计算中...',  # 预估转码大小
            'transcoded_size': '-',
            'completed_time': '-',
            'duration': '-',
            'operation': '-',  # 执行操作
            'status': '待执行',
            'start_time': None,
            'end_time': None
        }

        self.tasks.append(task)
        self.update_task_display()

        # 在后台线程中计算预估大小
        threading.Thread(target=self.calculate_and_update_estimate, args=(task,), daemon=True).start()

    def calculate_and_update_estimate(self, task):
        """在后台线程中计算预估大小并更新界面"""
        est_output_size = self.estimate_output_size(task['file_path'])
        if est_output_size == -1:
            task['estimated_size'] = '预估失败'
        else:
            est_output_size_mb = round(est_output_size / 1024 / 1024, 2)
            task['estimated_size'] = f"{est_output_size_mb} MB"

        # 在主线程中更新界面
        self.root.after(0, self.update_task_display)

    def update_task_display(self):
        """更新任务列表显示"""
        # 清空现有项目
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        # 添加任务到列表
        for i, task in enumerate(self.tasks, 1):  # 从1开始编号
            # 获取预估大小，如果任务中没有预估大小则显示'-'
            estimated_size = task.get('estimated_size', '-')
            operation = task.get('operation', '-')
            self.task_tree.insert('', 'end', values=(
                i,  # 序号
                task['filename'],
                task['original_size'],
                estimated_size,  # 预估转码大小
                task['transcoded_size'],
                task['completed_time'],
                task['duration'],
                operation,  # 执行操作
                task['status']
            ), tags=(task['id'],))

        # 更新统计信息
        self.update_task_stats()

    def format_file_size(self, size_bytes):
        """格式化文件大小显示"""
        if size_bytes == 0:
            return "0B"
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"

    def update_task_stats(self):
        """更新任务统计信息"""
        total = len(self.tasks)
        pending = 0
        completed = 0
        failed = 0

        for task in self.tasks:
            status = task['status']
            if status == '待执行':
                pending += 1
            elif status == '已完成' or status == '仅改名':
                completed += 1
            elif status == '执行失败':
                failed += 1
            elif status == '不执行转码，只改名复制':
                # 包含"不执行转码，只改名复制"这类状态
                completed += 1

        stats_text = f"任务统计：共{total}个任务，待处理{pending}个，已完成{completed}个，失败{failed}个"
        self.stats_label.config(text=stats_text)

    def on_task_double_click(self, event):
        """处理任务列表双击事件（用于删除任务）"""
        # 获取被点击的项目
        item = self.task_tree.identify('item', event.x, event.y)
        if item:
            # 获取该任务的ID
            values = self.task_tree.item(item, 'values')
            filename = values[1]  # 文件名仍然是第二列（第一列是序号）

            # 找到对应的任务
            task_to_remove = None
            for task in self.tasks:
                if task['filename'] == filename:
                    task_to_remove = task
                    break

            if task_to_remove:
                # 检查任务状态，如果正在执行，需要确认
                if task_to_remove['status'] == '执行中':
                    result = messagebox.askyesno("确认", f"任务 '{filename}' 正在执行，确定要中止并删除吗？")
                    if result:
                        # 中止任务（设置运行标志为False以停止任务）
                        self.running = False
                        # 从任务列表中移除
                        self.tasks.remove(task_to_remove)
                        self.update_task_display()
                else:
                    # 非执行中的任务直接删除
                    self.tasks.remove(task_to_remove)
                    self.update_task_display()

    def task_control(self):
        """任务控制（开始/暂停/继续）"""
        if not self.running:
            # 如果没有运行，则开始任务
            self.start_tasks()
        else:
            # 如果正在运行，则暂停/继续
            self.pause_tasks()

    def start_tasks(self):
        """开始执行任务"""
        if not self.tasks:
            messagebox.showinfo("提示", "没有任务可执行")
            return

        self.running = True
        self.paused = False
        self.task_control_button.config(text="暂停任务")
        self.config_button.config(state='disabled')  # 运行中禁用配置按钮

        # 启动任务执行线程
        task_thread = threading.Thread(target=self.execute_tasks)
        task_thread.daemon = True
        task_thread.start()

    def pause_tasks(self):
        """暂停任务"""
        if not self.running:
            messagebox.showinfo("提示", "没有正在运行的任务")
            return

        self.paused = not self.paused
        if self.paused:
            self.task_control_button.config(text="继续任务")
        else:
            self.task_control_button.config(text="暂停任务")

    def clear_completed_tasks(self):
        """清空已完成的任务"""
        self.tasks = [task for task in self.tasks if task['status'] not in ['已完成', '仅改名']]
        self.update_task_display()

    def execute_tasks(self):
        """执行转码任务"""
        completed_count = 0

        for i, task in enumerate(self.tasks):
            if not self.running:
                break

            # 更新队列进度条
            self.root.after(0, lambda x=i, total=len(self.tasks): self.update_queue_progress(x, total))

            if task['status'] == '待执行':
                task['status'] = '执行中'
                task['start_time'] = time.time()
                # 重置当前任务进度条
                self.root.after(0, self.reset_current_progress)
                self.root.after(0, self.update_task_display)

                # 执行转码
                success = self.transcode_video(task)

                task['end_time'] = time.time()
                duration = task['end_time'] - task['start_time']
                task['duration'] = f"{duration:.2f}秒"
                task['completed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if success:
                    task['status'] = '已完成'
                    completed_count += 1
                else:
                    task['status'] = '执行失败'

                self.root.after(0, self.update_task_display)
            elif task['status'] == '仅改名':
                # 对于仅改名的任务，直接标记为已完成
                task['operation'] = '仅改名'
                task['status'] = '已完成'
                task['duration'] = '0.00秒'
                task['completed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                completed_count += 1
                self.root.after(0, self.update_task_display)

        # 完成所有任务后更新UI
        self.root.after(0, lambda: self.task_control_button.config(text="开始任务"))
        self.root.after(0, lambda: self.config_button.config(state='normal'))  # 恢复配置按钮
        self.root.after(0, self.set_queue_progress_100)
        # 完成后将当前任务进度条设置为0
        self.root.after(0, self.reset_current_progress)
        self.running = False
        self.paused = False

        # 保存日志
        self.save_log()

    def stop_all_tasks(self):
        """停止所有任务"""
        self.running = False

    def set_queue_progress_100(self):
        """设置队列进度条为100%"""
        self.queue_progress['value'] = 100

    def reset_current_progress(self):
        """重置当前任务进度条为0"""
        self.current_progress['value'] = 0

    def update_current_progress(self, value):
        """更新当前任务进度条"""
        self.current_progress['value'] = value

    def set_current_progress_100(self):
        """设置当前任务进度条为100%"""
        self.current_progress['value'] = 100

    def update_queue_progress(self, current, total):
        """更新队列进度条"""
        self.queue_progress['value'] = (current / total) * 100 if total > 0 else 0

    def open_config_dialog(self):
        """打开转码参数配置对话框"""
        config_window = tk.Toplevel(self.root)
        config_window.title("配置转码参数")
        config_window.geometry("600x400")
        config_window.transient(self.root)  # 设置为临时父窗口
        config_window.grab_set()  # 模态窗口

        # 默认转码参数
        default_params = (
            "-c:v libx264 -profile:v main -level 4.0 "
            "-crf 28 -preset medium "
            "-maxrate 8500000 -bufsize 17000000 "
            "-vf scale=w=min(iw\\,1920):h=-2:force_original_aspect_ratio=decrease,pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2:x=0:y=0:color=black,format=yuv420p "
            "-c:a aac -ac 2 -ar 44100 -b:a 128000 "
            "-r 30 "
            "-threads 0 "  # 全局自动适配核心（解码/过滤/编码均用最大可用线程）
            "-x264-params 'frame-threads=auto' "  # 启用 libx264 高效帧线程（自动适配）
            "-movflags +faststart -y -f mp4"
        )

        # 创建文本框
        ttk.Label(config_window, text="转码参数:").pack(anchor=tk.W, padx=10, pady=5)

        text_frame = ttk.Frame(config_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 使用Text控件，支持多行编辑
        self.param_text = tk.Text(text_frame, wrap=tk.WORD)
        self.param_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.param_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.param_text.configure(yscrollcommand=scrollbar.set)

        # 设置默认参数
        self.param_text.insert(tk.END, default_params)

        # 按钮框架
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # 确认和取消按钮
        ttk.Button(button_frame, text="确认", command=lambda: self.save_params(config_window)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="取消", command=config_window.destroy).pack(side=tk.LEFT)

    def save_params(self, window):
        """保存转码参数"""
        self.ffmpeg_params = self.param_text.get("1.0", tk.END).strip()
        window.destroy()

    def show_context_menu(self, event):
        """显示右键菜单"""
        # 选择被右键点击的项目
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)

        # 显示菜单
        try:
            self.task_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.task_context_menu.grab_release()

    def get_selected_task(self):
        """获取选中的任务"""
        selection = self.task_tree.selection()
        if selection:
            item = selection[0]  # 获取第一个选中的项目
            values = self.task_tree.item(item, 'values')
            filename = values[1]  # 文件名是第二列（第一列是序号）

            # 找到对应的任务
            for task in self.tasks:
                if task['filename'] == filename:
                    return task
        return None

    def open_selected_file(self):
        """打开选中的文件"""
        task = self.get_selected_task()
        if task:
            file_path = task['file_path']
            if os.path.exists(file_path):
                import platform
                import subprocess
                try:
                    if platform.system() == "Windows":
                        os.startfile(file_path)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", file_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", file_path])
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开文件: {str(e)}")
            else:
                messagebox.showerror("错误", "文件不存在")

    def open_selected_directory(self):
        """打开选中文件所在的目录"""
        task = self.get_selected_task()
        if task:
            file_path = task['file_path']
            directory = os.path.dirname(file_path)
            if os.path.exists(directory):
                import platform
                import subprocess
                try:
                    if platform.system() == "Windows":
                        os.startfile(directory)
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", directory])
                    else:  # Linux
                        subprocess.run(["xdg-open", directory])
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开目录: {str(e)}")
            else:
                messagebox.showerror("错误", "目录不存在")

    def delete_selected_task(self):
        """删除选中的任务"""
        task = self.get_selected_task()
        if task:
            filename = task['filename']
            # 检查任务状态，如果正在执行，需要确认
            if task['status'] == '执行中':
                result = messagebox.askyesno("确认", f"任务 '{filename}' 正在执行，确定要中止并删除吗？")
                if result:
                    # 中止任务（设置运行标志为False以停止任务）
                    self.running = False
                    # 从任务列表中移除
                    self.tasks.remove(task)
                    self.update_task_display()
            else:
                # 非执行中的任务直接删除
                self.tasks.remove(task)
                self.update_task_display()

    def rename_only(self):
        """只改名不转码"""
        task = self.get_selected_task()
        if task:
            filename = task['filename']
            original_status = task['status']
            original_file_path = task['file_path']

            # 检查任务状态，如果正在执行，则不允许只改名
            if task['status'] == '执行中':
                messagebox.showwarning("警告", f"任务 '{filename}' 正在执行，无法只改名")
                return

            # 获取新的文件名（应用关键字替换规则）
            name, ext = os.path.splitext(filename)
            replace_keyword = self.replace_keyword.get().strip()
            scan_keyword = self.scan_keyword.get().strip()

            if replace_keyword and scan_keyword and scan_keyword in name:
                # 替换文件名中的关键字
                new_name = name.replace(scan_keyword, replace_keyword)
                new_filename = new_name + ext

                # 构建新文件路径
                directory = os.path.dirname(original_file_path)
                new_file_path = os.path.join(directory, new_filename)

                try:
                    # 重命名实际文件
                    os.rename(original_file_path, new_file_path)

                    # 更新任务信息
                    task['file_path'] = new_file_path
                    task['filename'] = new_filename
                    task['operation'] = '仅改名'
                    task['status'] = '仅改名'
                    task['completed_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    task['duration'] = '0.00秒'

                    # 更新任务列表显示
                    self.update_task_display()
                    # messagebox.showinfo("成功", f"文件已重命名为: {new_filename}")
                except OSError as e:
                    messagebox.showerror("错误", f"重命名文件失败: {str(e)}")
            else:
                messagebox.showinfo("提示", f"文件名 '{filename}' 中不包含扫描关键字 '{scan_keyword}'，无需改名")

    def on_general_drop(self, event):
        """处理整个界面的拖拽事件"""
        files = self.root.tk.splitlist(event.data)
        if files:
            for file_path in files:
                if os.path.isfile(file_path):
                    # 如果是文件，添加到任务列表
                    self.video_file_path.set(file_path)
                    self.add_task(file_path)
                elif os.path.isdir(file_path):
                    # 如果是文件夹，设置到扫描文件夹路径
                    self.scan_folder_path.set(file_path)

    def transcode_video(self, task):
        """执行视频转码"""
        # 检查是否暂停
        while self.paused and self.running:
            time.sleep(1)

        if not self.running:
            return False

        input_path = task['file_path']
        output_path = self.get_output_path(input_path)

        # 预估输出体积
        est_output_size = self.estimate_output_size(input_path)
        if est_output_size == -1:
            # 预估失败，直接执行转码
            task['estimated_size'] = '预估失败'  # 记录预估大小
            task['status'] = '执行中（预估失败）'
            print(f"预估输出体积失败，直接执行转码: {input_path}")
        else:
            # 计算源文件大小
            original_size = os.path.getsize(input_path)
            original_size_mb = round(original_size / 1024 / 1024, 2)
            est_output_size_mb = round(est_output_size / 1024 / 1024, 2)

            # 记录预估大小
            task['estimated_size'] = f"{est_output_size_mb} MB"
            print(f"源文件体积：{original_size_mb} MB，预估输出体积：{est_output_size_mb} MB")

            # 只记录预估信息，不管预估值如何都执行转码
            task['status'] = f'执行中（预估体积为 {est_output_size_mb} MB）'
            print(f"执行转码: {input_path}")

        try:
            # 获取视频时长用于计算进度
            duration_cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{input_path}"'
            duration_result = subprocess.run(
                duration_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            try:
                duration = float(duration_result.stdout.strip())
            except ValueError:
                duration = 0  # 如果无法获取时长，设为0

            # 转码后输出到指定路径
            cmd_str = f'ffmpeg -i "{input_path}" {self.ffmpeg_params} "{output_path}"'
            temp_output_path = None

            # 执行转码命令并实时获取输出
            process = subprocess.Popen(
                cmd_str,
                shell=True,  # 使用shell=True来正确处理引号
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
                encoding='utf-8'
            )

            # 收集错误信息
            error_output = ""

            # 实时读取FFmpeg输出并更新进度
            while True:
                # 检查是否暂停
                while self.paused and self.running:
                    time.sleep(1)

                if not self.running:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    return False

                if process.stderr is not None:
                    output = process.stderr.readline()
                    if output == '' and process.poll() is not None:
                        break

                    if output:
                        # 将输出添加到错误信息中（包括进度信息）
                        error_output += output

                        # 解析FFmpeg输出，获取进度信息
                        if 'time=' in output and duration > 0:
                            # 从输出中提取当前时间
                            time_parts = output.split('time=')
                            if len(time_parts) > 1:
                                time_str = time_parts[1].split()[0]  # 获取时间字符串
                                try:
                                    # 解析时间格式 HH:MM:SS 或 HH:MM:SS.ms
                                    time_parts = time_str.split(':')
                                    if len(time_parts) == 3:
                                        hours, minutes, seconds = time_parts
                                        if '.' in seconds:
                                            seconds, ms = seconds.split('.')
                                        else:
                                            ms = 0
                                        current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                                        progress = min(100, (current_time / duration) * 100)
                                        # 在主线程中更新进度条
                                        self.root.after(0, lambda prog=progress: self.update_current_progress(prog))
                                except ValueError:
                                    pass  # 解析时间失败，继续处理
                else:
                    # 如果stderr为None，检查进程是否结束
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)  # 短暂休眠避免CPU占用过高

            # 获取进程返回码
            return_code = process.returncode

            if return_code == 0:
                # 获取转码后文件大小
                if os.path.exists(output_path):
                    transcoded_size = os.path.getsize(output_path)
                    original_size = os.path.getsize(input_path)  # 获取原文件大小

                    # 检查转码后的文件是否大于原文件的80%
                    if transcoded_size > original_size * 0.8:
                        # 转码后文件大于原文件的80%，用原文件替换转码文件
                        import shutil
                        shutil.copy2(input_path, output_path)  # 复制原文件到输出路径

                        # 更新任务状态和大小信息
                        task['operation'] = f'转码后体积: {self.format_file_size(transcoded_size)}，执行复制原文件'
                        task['transcoded_size'] = self.format_file_size(original_size)
                        task['status'] = '已完成'
                        # 进度条设为100%
                        self.root.after(0, self.set_current_progress_100)
                        return True
                    else:
                        task['operation'] = '已转码'
                        task['transcoded_size'] = self.format_file_size(transcoded_size)
                        # 转码完成，进度条设为100%
                        self.root.after(0, self.set_current_progress_100)
                        return True
                else:
                    print(f"转码完成但输出文件不存在: {output_path}")
                    task['error_message'] = f"转码完成但输出文件不存在: {output_path}"
                    return False
            else:
                print(f"转码失败: {error_output}")
                task['error_message'] = f"转码失败: {error_output}"
                return False

        except subprocess.TimeoutExpired:
            print("转码超时")
            task['error_message'] = "转码超时"
            return False
        except FileNotFoundError:
            print("未找到FFmpeg，请确保已安装FFmpeg并添加到系统PATH")
            task['error_message'] = "未找到FFmpeg，请确保已安装FFmpeg并添加到系统PATH"
            return False
        except Exception as e:
            print(f"转码异常: {str(e)}")
            task['error_message'] = str(e)
            return False

    def get_video_bitrate(self, input_path):
        """获取视频平均码率（bps）"""
        try:
            # 尝试获取视频流的码率
            cmd = f'ffprobe -v quiet -select_streams v:0 -show_entries stream=bit_rate -of default=noprint_wrappers=1:nokey=1 "{input_path}"'
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            source_vbr = result.stdout.strip()
            if source_vbr and source_vbr != 'N/A' and source_vbr != '0':
                source_vbr = int(source_vbr)
            else:
                # 如果获取不到码率，通过文件大小和时长计算
                duration_cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{input_path}"'
                duration_result = subprocess.run(
                    duration_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                duration = float(duration_result.stdout.strip())
                file_size = os.path.getsize(input_path)
                source_vbr = int((file_size * 8) / duration)

            return source_vbr
        except Exception as e:
            print(f"获取视频码率失败: {str(e)}")
            # 备用方案：通过文件大小和时长计算
            try:
                duration_cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{input_path}"'
                duration_result = subprocess.run(
                    duration_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )
                duration = float(duration_result.stdout.strip())
                file_size = os.path.getsize(input_path)
                return int((file_size * 8) / duration)
            except:
                return 0  # 如果都无法获取，则返回0

    def estimate_output_size(self, input_path):
        """预估转码后输出体积 - 使用更精确的算法"""
        try:
            # 获取视频流码率
            cmd = f'ffprobe -v quiet -select_streams v:0 -show_entries stream=bit_rate -of csv=p=0 "{input_path}"'
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True, encoding='utf-8')
            video_bitrate = 0
            if result.stdout.strip() and result.stdout.strip() != 'N/A':
                try:
                    video_bitrate = int(result.stdout.strip())
                except ValueError:
                    video_bitrate = 0

            # 如果无法获取视频流码率，回退到原来的方法
            if video_bitrate == 0:
                video_bitrate = self.get_video_bitrate(input_path)
                if video_bitrate == 0:
                    # 如果还是无法获取码率，尝试使用文件大小和时长计算
                    duration_cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{input_path}"'
                    duration_result = subprocess.run(
                        duration_cmd,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8'
                    )
                    try:
                        duration = float(duration_result.stdout.strip())
                        file_size = os.path.getsize(input_path)
                        video_bitrate = int((file_size * 8) / duration)
                    except:
                        return -1  # 无法计算预估体积

            # 获取音频流码率
            cmd = f'ffprobe -v quiet -select_streams a:0 -show_entries stream=bit_rate -of csv=p=0 "{input_path}"'
            audio_result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True, encoding='utf-8')
            audio_bitrate = 128000  # 默认音频码率
            if audio_result.stdout.strip() and audio_result.stdout.strip() != 'N/A':
                try:
                    audio_bitrate = int(audio_result.stdout.strip())
                except ValueError:
                    audio_bitrate = 128000  # 默认128kbps

            # 获取原视频分辨率
            cmd = f'ffprobe -v quiet -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "{input_path}"'
            res_result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True, encoding='utf-8')
            width, height = 1920, 1080  # 默认1080P
            if res_result.stdout.strip():
                try:
                    res_parts = res_result.stdout.strip().split('x')
                    if len(res_parts) == 2:
                        width, height = map(int, res_parts)
                except:
                    width, height = 1920, 1080

            # 计算分辨率缩放比例（相对于1080P）
            res_scale = (width * height) / (1920 * 1080)

            # 基于CRF模式的预估 - 对于CRF 28，不同内容类型的码率模型
            # 动作片、体育节目等复杂内容: 通常需要更高码率
            # 纪录片、访谈节目等简单内容: 可以用较低码率

            # 估算内容复杂度 - 暂时使用基于分辨率和源码率的简化模型
            # 对于复杂内容，实际码率可能更高
            complexity_factor = 1.0

            # 简化的内容复杂度估算 - 如果源码率高于平均水平，则可能是复杂内容
            if video_bitrate > 8000000:  # 超过8Mbps认为是高复杂度
                complexity_factor = 1.2
            elif video_bitrate > 5000000:  # 5-8Mbps之间
                complexity_factor = 1.1
            else:  # 低于5Mbps
                complexity_factor = 0.9

            # 目标视频码率计算 (基于CRF 28 + 复杂度调整 + 分辨率调整)
            # CRF 28在1080P下平均码率大约在3-4Mbps左右，根据内容和分辨率调整
            base_target_rate = 3500000  # 基础目标码率3.5Mbps（CRF 28下的1080P参考值）
            target_video_rate = int(base_target_rate * res_scale * complexity_factor)

            # 确保码率在合理范围内
            if target_video_rate > self.MAX_MAXRATE:
                target_video_rate = self.MAX_MAXRATE

            # 获取视频时长
            duration_cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{input_path}"'
            duration_result = subprocess.run(
                duration_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            duration = float(duration_result.stdout.strip())

            # 预估输出体积 = (目标视频码率 + 音频码率) * 时长 / 8 * 1.01 (1%开销)
            est_output_size = int((target_video_rate + self.AUDIO_BITRATE) * duration / 8 * 1.01)
            return est_output_size
        except Exception as e:
            print(f"预估输出体积失败: {str(e)}")
            return -1  # 预估失败

    def get_output_path(self, input_path):
        """获取输出文件路径"""
        if self.overwrite_var.get():
            # 转码后输出到原目录 - 保存到原文件所在目录
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)

            # 检查是否需要进行关键字替换
            replace_keyword = self.replace_keyword.get().strip()
            scan_keyword = self.scan_keyword.get().strip()

            if replace_keyword and scan_keyword and scan_keyword in name:
                # 替换文件名中的关键字
                name = name.replace(scan_keyword, replace_keyword)

            # 获取原文件所在目录
            output_dir = os.path.dirname(input_path)

            # 检查转码参数是否包含 -f mp4，如果是则强制使用 .mp4 扩展名
            if "-f mp4" in self.ffmpeg_params or "-fmp4" in self.ffmpeg_params:
                return os.path.join(output_dir, f"{name}_transcoded.mp4")
            else:
                return os.path.join(output_dir, f"{name}_transcoded{ext}")
        else:
            # 不输出到原目录 - 保存到桌面的"当前日期、时间+转码后文件"文件夹
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)

            # 检查是否需要进行关键字替换
            replace_keyword = self.replace_keyword.get().strip()
            scan_keyword = self.scan_keyword.get().strip()

            if replace_keyword and scan_keyword and scan_keyword in name:
                # 替换文件名中的关键字
                name = name.replace(scan_keyword, replace_keyword)

            # 获取当前日期时间
            current_date = datetime.now().strftime('%Y-%m-%d')

            # 获取桌面路径
            desktop_path = str(Path.home() / "Desktop")

            # 创建带当前时间的文件夹
            output_dir = os.path.join(desktop_path, f"{current_date}_转码后文件")
            os.makedirs(output_dir, exist_ok=True)

            # 检查转码参数是否包含 -f mp4，如果是则强制使用 .mp4 扩展名
            if "-f mp4" in self.ffmpeg_params or "-fmp4" in self.ffmpeg_params:
                return os.path.join(output_dir, f"{name}_transcoded.mp4")
            else:
                return os.path.join(output_dir, f"{name}_transcoded{ext}")

    def save_log(self):
        """保存日志到文件"""
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")

        with open(log_path, "w", encoding="utf-8-sig") as f:  # 使用utf-8-sig避免BOM问题
            f.write(f"转码任务日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")

            for task in self.tasks:
                f.write(f"文件名: {task['filename']}\n")
                f.write(f"原文件大小: {task['original_size']}\n")
                f.write(f"转码后大小: {task['transcoded_size']}\n")
                f.write(f"转码用时: {task['duration']}\n")
                f.write(f"执行操作: {task['operation']}\n")
                f.write(f"转码状态: {task['status']}\n")

                if task['status'] == '执行失败':
                    error_msg = task.get('error_message', '转码失败')
                    f.write(f"错误信息: {error_msg}\n")

                f.write("-" * 30 + "\n")

        # 额外保存一份详细日志到输出文件夹
        self.save_detailed_log_to_output_folder()

    def save_detailed_log_to_output_folder(self):
        """保存详细日志到输出文件夹"""
        try:
            # 获取当前时间戳用于创建日志文件夹
            current_date = datetime.now().strftime('%Y-%m-%d')
            desktop_path = str(Path.home() / "Desktop")
            output_dir = os.path.join(desktop_path, f"{current_date}_转码后文件")
            os.makedirs(output_dir, exist_ok=True)

            # 创建详细日志文件
            detailed_log_path = os.path.join(output_dir, f"转码任务详细日志_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")

            with open(detailed_log_path, "w", encoding="utf-8-sig") as f:
                f.write(f"转码任务详细日志 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                f.write(f"{'序号':<4} {'文件名':<30} {'原文件大小':<12} {'预估转码大小':<15} {'转码后大小':<12} {'完成时间':<20} {'转码用时':<10} {'执行操作':<12} {'转码状态':<12}\n")
                f.write("-" * 140 + "\n")

                for i, task in enumerate(self.tasks, 1):
                    # 限制文件名长度以适应表格
                    filename = task['filename'][:28] + "..." if len(task['filename']) > 28 else task['filename']

                    f.write(f"{i:<4} {filename:<30} {task['original_size']:<12} {task['estimated_size']:<15} "
                           f"{task['transcoded_size']:<12} {task['completed_time']:<20} {task['duration']:<10} "
                           f"{task['operation']:<12} {task['status']:<12}\n")

                f.write("\n" + "="*60 + "\n")
                f.write("详细任务信息:\n\n")

                for task in self.tasks:
                    f.write(f"文件名: {task['filename']}\n")
                    f.write(f"文件路径: {task['file_path']}\n")
                    f.write(f"原文件大小: {task['original_size']}\n")
                    f.write(f"预估转码大小: {task['estimated_size']}\n")
                    f.write(f"转码后大小: {task['transcoded_size']}\n")
                    f.write(f"完成时间: {task['completed_time']}\n")
                    f.write(f"转码用时: {task['duration']}\n")
                    f.write(f"执行操作: {task['operation']}\n")
                    f.write(f"转码状态: {task['status']}\n")

                    if task.get('error_message'):
                        f.write(f"错误信息: {task['error_message']}\n")

                    f.write("-" * 50 + "\n")
        except Exception as e:
            print(f"保存详细日志到输出文件夹失败: {str(e)}")

    def calculate_all_estimates(self):
        """计算所有任务的预估大小"""
        if not self.tasks:
            messagebox.showinfo("提示", "没有任务需要计算预估大小")
            return

        # 更新所有任务的预估大小状态
        for task in self.tasks:
            if task['status'] == '待执行':  # 只对未执行的任务计算预估大小
                task['estimated_size'] = '计算中...'
        self.update_task_display()

        # 在后台线程中计算所有任务的预估大小
        threading.Thread(target=self.calculate_all_estimates_thread, daemon=True).start()

    def calculate_all_estimates_thread(self):
        """在后台线程中计算所有任务的预估大小"""
        for task in self.tasks:
            if task['status'] == '待执行':  # 只对未执行的任务计算预估大小
                est_output_size = self.estimate_output_size(task['file_path'])
                if est_output_size == -1:
                    task['estimated_size'] = '预估失败'
                else:
                    est_output_size_mb = round(est_output_size / 1024 / 1024, 2)
                    task['estimated_size'] = f"{est_output_size_mb} MB"

        # 在主线程中更新界面
        self.root.after(0, self.update_task_display)


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = VideoTranscoderApp(root)
    root.mainloop()