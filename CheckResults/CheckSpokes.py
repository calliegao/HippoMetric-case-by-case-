import vtk

def read_vtk_points(file_path):
    """
    读取 VTK 文件并返回点数据（numpy 格式）。
    """
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(file_path)
    reader.Update()
    poly_data = reader.GetOutput()
    points = poly_data.GetPoints()
    point_list = []
    for i in range(points.GetNumberOfPoints()):
        point_list.append(points.GetPoint(i))
    return point_list

def main():
    # 输入文件路径
    surface_file = "Remesh_CA1_transformed.vtk"
    ps_file = "CA1_ps_refined.vtk"
    pt_file = "CA1_pt_refined.vtk"

    # 读取曲面
    surface_reader = vtk.vtkPolyDataReader()
    surface_reader.SetFileName(surface_file)
    surface_reader.Update()
    surface = surface_reader.GetOutput()

    # 设置曲面属性
    surface_mapper = vtk.vtkPolyDataMapper()
    surface_mapper.SetInputData(surface)

    surface_actor = vtk.vtkActor()
    surface_actor.SetMapper(surface_mapper)
    surface_actor.GetProperty().SetColor(0.5, 0.5, 0.5)  # 灰色
    surface_actor.GetProperty().SetOpacity(0.5)  # 半透明

    # 读取向量起点和终点
    ps_points = read_vtk_points(ps_file)
    pt_points = read_vtk_points(pt_file)

    # 创建表示向量的PolyData
    vector_poly_data = vtk.vtkPolyData()
    vector_points = vtk.vtkPoints()
    vector_lines = vtk.vtkCellArray()

    for i in range(len(ps_points)):
        start_point = ps_points[i]
        end_point = pt_points[i]

        start_id = vector_points.InsertNextPoint(start_point)
        end_id = vector_points.InsertNextPoint(end_point)

        # 创建线元
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, start_id)
        line.GetPointIds().SetId(1, end_id)
        vector_lines.InsertNextCell(line)

    vector_poly_data.SetPoints(vector_points)
    vector_poly_data.SetLines(vector_lines)

    # 设置向量的Mapper和Actor
    vector_mapper = vtk.vtkPolyDataMapper()
    vector_mapper.SetInputData(vector_poly_data)

    vector_actor = vtk.vtkActor()
    vector_actor.SetMapper(vector_mapper)
    vector_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # 红色
    vector_actor.GetProperty().SetLineWidth(2)  # 设置线宽

    # 渲染器和窗口
    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window_interactor = vtk.vtkRenderWindowInteractor()
    render_window_interactor.SetRenderWindow(render_window)

    # 添加Actor到渲染器
    renderer.AddActor(surface_actor)
    renderer.AddActor(vector_actor)
    renderer.SetBackground(0.1, 0.1, 0.1)  # 背景颜色为黑色

    # 开始渲染
    render_window.Render()
    render_window_interactor.Start()

if __name__ == "__main__":
    main()
