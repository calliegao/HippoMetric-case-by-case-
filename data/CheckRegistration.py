import os
import vtk

# 定义输入和输出路径
reged_refined_surf_folder = "/data03/ng/adni_test/data/RegedRefinedSurf"
output_pic_folder = "/data03/ng/adni_test/pic"
left_template = "/data03/ng/adni_test/data/left_hippo.vtk"
right_template = "/data03/ng/adni_test/data/right_hippo.vtk"

# 确保输出路径存在
os.makedirs(output_pic_folder, exist_ok=True)

def visualize_and_save(vtk_file, template_file, output_path):
    """
    可视化两个三维模型并保存为图片。
    
    :param vtk_file: 配准后的 vtk 文件路径
    :param template_file: 对应的模板 vtk 文件路径
    :param output_path: 输出图片路径
    """
    # 加载模型
    reader_vtk = vtk.vtkPolyDataReader()
    reader_vtk.SetFileName(vtk_file)
    reader_vtk.Update()
    vtk_mesh = reader_vtk.GetOutput()

    reader_template = vtk.vtkPolyDataReader()
    reader_template.SetFileName(template_file)
    reader_template.Update()
    template_mesh = reader_template.GetOutput()

    # 创建渲染器
    renderer = vtk.vtkRenderer()

    # 设置背景色
    renderer.SetBackground(1, 1, 1)  # 白色背景

    # 创建渲染窗口
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)

    # 创建窗口交互器
    render_window_interactor = vtk.vtkRenderWindowInteractor()
    render_window_interactor.SetRenderWindow(render_window)

    # 创建模板和配准后的曲面的映射器
    template_mapper = vtk.vtkPolyDataMapper()
    template_mapper.SetInputData(template_mesh)

    vtk_mapper = vtk.vtkPolyDataMapper()
    vtk_mapper.SetInputData(vtk_mesh)

    # 创建模板和配准后曲面的演员（actor）
    template_actor = vtk.vtkActor()
    template_actor.SetMapper(template_mapper)
    template_actor.GetProperty().SetColor(0, 1, 0)  # 绿色
    template_actor.GetProperty().SetOpacity(0.5)

    vtk_actor = vtk.vtkActor()
    vtk_actor.SetMapper(vtk_mapper)
    vtk_actor.GetProperty().SetColor(1, 0, 0)  # 红色
    vtk_actor.GetProperty().SetOpacity(0.7)

    # 添加演员到渲染器
    renderer.AddActor(template_actor)
    renderer.AddActor(vtk_actor)

    # 设置光源
    light = vtk.vtkLight()
    light.SetPosition(1, 1, 1)  # 设置光源位置
    light.SetFocalPoint(0, 0, 0)  # 设置光源聚焦点
    renderer.AddLight(light)

    # 设置相机位置
    renderer.GetActiveCamera().SetPosition(0, 0, 1)
    renderer.GetActiveCamera().SetFocalPoint(0, 0, 0)
    renderer.GetActiveCamera().SetViewUp(0, 1, 0)

    # 渲染并保存截图
    render_window.Render()
    window_to_image_filter = vtk.vtkWindowToImageFilter()
    window_to_image_filter.SetInput(render_window)
    window_to_image_filter.Update()

    # 保存图片
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(output_path)
    writer.SetInputData(window_to_image_filter.GetOutput())
    writer.Write()

    print(f"Saved visualization to: {output_path}")

# 遍历文件夹
for side in ["Left", "Right"]:
    template_file = left_template if side == "Left" else right_template
    side_folder = os.path.join(reged_refined_surf_folder, side)
    for study in os.listdir(side_folder):
        study_folder = os.path.join(side_folder, study)
        if not os.path.isdir(study_folder):
            continue
        for subject in os.listdir(study_folder):
            subject_folder = os.path.join(study_folder, subject)
            if not os.path.isdir(subject_folder):
                continue
            for scan in os.listdir(subject_folder):
                scan_folder = os.path.join(subject_folder, scan)
                vtk_file = os.path.join(scan_folder, "Remesh_combined_label_transformed.vtk")
                if os.path.exists(vtk_file):
                    # 构造输出路径
                    output_scan_folder = os.path.join(output_pic_folder, side, study, subject)
                    os.makedirs(output_scan_folder, exist_ok=True)
                    output_path = os.path.join(output_scan_folder, f"{scan}.png")
                    
                    # 可视化并保存
                    visualize_and_save(vtk_file, template_file, output_path)
