import os

EXCLUDE_DIRS = {'__pycache__', '.git', '.idea', '.vscode'}
EXCLUDE_FILES = {'.DS_Store'}


def print_tree(start_path, prefix=""):
    try:
        items = [
            item for item in sorted(os.listdir(start_path))
            if not item.startswith('.') and  # 过滤隐藏文件/文件夹
               item not in EXCLUDE_FILES and
               item not in EXCLUDE_DIRS
        ]
    except PermissionError:
        return  # 跳过无权限目录

    pointers = ['├── '] * (len(items) - 1) + ['└── ']  # 树形符号

    for pointer, item in zip(pointers, items):
        path = os.path.join(start_path, item)
        print(prefix + pointer + item)
        if os.path.isdir(path):
            extension = '│   ' if pointer == '├── ' else '    '
            print_tree(path, prefix + extension)


# 用你项目根路径替换这里
project_path = "/Users/apple/Documents/BabyApp/my_first_app/lib/generated"
print(project_path + "/")
print_tree(project_path)
