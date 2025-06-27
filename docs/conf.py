# -- 配置导入与信息 -----------------------------------------------------
import os
import sys
from sphinx.util.fileutil import copy_asset  # ✅ 你缺少这个导入

# -- 项目信息 -----------------------------------------------------------
project = 'HippoMetric'
copyright = '2025, Na Gao'
author = 'Na Gao'
release = '0.1'

# -- 常规配置 -----------------------------------------------------------
extensions = [
    'myst_parser',           # ✅ 支持 Markdown
    'sphinx_rtd_theme',      # ✅ 使用 RTD 主题
]

templates_path = ['_templates']
exclude_patterns = []

language = 'en'

# -- 支持 Markdown 文件 -------------------------------------------------
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# -- HTML 输出配置 -------------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']  # ✅ 保留 _static 目录

# -- 添加 images 文件夹拷贝功能 ------------------------------------------
def setup(app):
    app.connect(
        'builder-inited',
        lambda app: copy_asset(
            os.path.abspath('source/images'),          # 源路径
            os.path.join(app.outdir, '_static/images') # 目标路径
        )
    )
