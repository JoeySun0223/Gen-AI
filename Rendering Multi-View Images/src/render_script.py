import bpy
import os
from mathutils import Vector
import math
import sys


def load_3Dmodel(file_path):
    """
    加载3D模型文件
    
    参数:
        file_path: 模型文件的完整路径
    """
    # 确保文件存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    # 清空当前Blender场景
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    # 根据文件扩展名选择适当的导入方法
    file_ext = os.path.splitext(file_path)[1].lower()
    
    if file_ext == '.blend':
        # 导入.blend文件
        with bpy.data.libraries.load(file_path, link=False) as (data_from, data_to):
            data_to.objects = [name for name in data_from.objects]
            
        # 添加导入的对象到场景
        for obj in data_to.objects:
            if obj is not None:
                bpy.context.collection.objects.link(obj)
                
    elif file_ext == '.obj':
        # 导入OBJ文件
        bpy.ops.import_scene.obj(filepath=file_path)
        
    elif file_ext == '.fbx':
        # 导入FBX文件
        bpy.ops.import_scene.fbx(filepath=file_path)
        
    elif file_ext == '.stl':
        # 导入STL文件
        bpy.ops.import_mesh.stl(filepath=file_path)
        
    elif file_ext == '.glb' or file_ext == '.gltf':
        # 导入glTF文件
        bpy.ops.import_scene.gltf(filepath=file_path)
        
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")
    
    print(f"成功导入模型: {file_path}")


def combine_objects():

    # Get all mesh objects
    imported_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

    if not imported_objects:
        print("No mesh objects found. Ensure the model is correctly imported!")
        return None

    # Apply transformations to all objects
    for obj in imported_objects:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Select all objects
    for obj in imported_objects:
        obj.select_set(True)

    # Join all objects into a single object
    bpy.context.view_layer.objects.active = imported_objects[0]
    bpy.ops.object.join()

    # Get the combined object
    combined_object = bpy.context.object
    combined_object.name = "Combined_Object"

    return combined_object

def move_bbox_to_origin(obj):

    # Get the bounding box vertices of the object
    bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    # Calculate the center of the bounding box
    bbox_center = sum(bbox, Vector()) / 8

    # Move the object
    obj.location -= bbox_center

def setup_lights():

    center_light_data = bpy.data.lights.new(name="Center_Light", type='POINT')
    center_light = bpy.data.objects.new(name="Center_Light", object_data=center_light_data)
    bpy.context.collection.objects.link(center_light)
    center_light.location = (0, 0, 2)
    center_light.data.energy = 200

    diagonal_positions = [
        (-2, -2, 2),
        (2, -2, 2),
        (-2, 2, 2),
        (2, 2, 2)
    ]

    for i, pos in enumerate(diagonal_positions):
        light_data = bpy.data.lights.new(name=f"Diagonal_Light_{i+1}", type='POINT')
        light_object = bpy.data.objects.new(name=f"Diagonal_Light_{i+1}", object_data=light_data)
        bpy.context.collection.objects.link(light_object)
        light_object.location = pos
        light_object.data.energy = 150

def render_views(output_dir, angle_step=30, distance=5.0):
    """
    从360度环绕视角渲染对象
    
    参数:
        output_dir: 输出目录路径
        angle_step: 角度间隔，默认30度
        distance: 相机与模型的距离
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 设置相机
    camera_data = bpy.data.cameras.new(name="Camera")
    camera_object = bpy.data.objects.new("Camera", camera_data)
    bpy.context.collection.objects.link(camera_object)
    bpy.context.scene.camera = camera_object

    # 渲染360度视图，每隔angle_step度一张
    for angle_deg in range(0, 360, angle_step):
        # 将角度转换为弧度
        angle_rad = math.radians(angle_deg)
        
        # 计算相机位置（水平圆形轨道）
        x = distance * math.cos(angle_rad)
        y = distance * math.sin(angle_rad)
        z = 0  # 保持在同一水平面
        
        # 设置相机位置
        camera_object.location = (x, y, z)
        
        # 使相机朝向原点（模型中心）
        direction = Vector((0, 0, 0)) - Vector(camera_object.location)
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera_object.rotation_euler = rot_quat.to_euler()
        
        # 设置渲染输出文件
        bpy.context.scene.render.filepath = os.path.join(output_dir, f"angle_{angle_deg:03d}.png")
        
        # 进行渲染
        bpy.ops.render.render(write_still=True)
        print(f"角度 {angle_deg}° 渲染完成，保存至 {bpy.context.scene.render.filepath}")


def save_combined_object(output_dir, model_name):
    """
    保存合并后的对象到blend文件
    
    参数:
        output_dir: 输出目录
        model_name: 模型名称
    """
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 构建输出文件路径
    output_file = os.path.join(output_dir, f"{model_name}_final.blend")

    # 保存当前场景为.blend文件
    bpy.ops.wm.save_as_mainfile(filepath=output_file)
    print(f"模型已保存至: {output_file}")


def normalize_model_size(obj, target_size=2.0):
    """
    规范化模型大小，确保其最大尺寸为目标大小
    
    参数:
        obj: 要规范化的对象
        target_size: 目标最大尺寸，默认为2.0单位
    """
    # 获取对象的当前尺寸
    dimensions = obj.dimensions
    max_dimension = max(dimensions.x, dimensions.y, dimensions.z)
    
    print(f"模型原始尺寸: X={dimensions.x:.4f}, Y={dimensions.y:.4f}, Z={dimensions.z:.4f}")
    
    if max_dimension == 0:
        print("警告: 对象尺寸为零，无法规范化大小")
        return
    
    # 计算缩放比例
    scale_factor = target_size / max_dimension
    
    # 应用统一缩放
    obj.scale = obj.scale * scale_factor
    
    # 应用变换使缩放生效
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
    # 验证新尺寸
    new_dimensions = obj.dimensions
    print(f"模型规范化后尺寸: X={new_dimensions.x:.4f}, Y={new_dimensions.y:.4f}, Z={new_dimensions.z:.4f}")
    print(f"缩放比例: {scale_factor:.4f}")


def get_model_path_from_args():
    """
    从命令行参数获取模型文件路径
    格式: blender --background --python render_script.py -- model_filename
    
    返回值:
        (model_path, model_name): 模型文件完整路径和不带扩展名的文件名
    """
    # 获取脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(script_dir, "model")
    
    # 查找"--"之后的参数
    try:
        idx = sys.argv.index("--")
        if idx < len(sys.argv) - 1:
            # 获取模型文件名
            model_filename = sys.argv[idx + 1]
            
            # 处理仅提供文件名而没有扩展名的情况
            if not os.path.splitext(model_filename)[1]:
                # 寻找匹配的文件
                potential_files = []
                for ext in ['.blend', '.obj', '.fbx', '.stl', '.glb', '.gltf']:
                    test_path = os.path.join(model_dir, f"{model_filename}{ext}")
                    if os.path.exists(test_path):
                        potential_files.append(test_path)
                
                if len(potential_files) == 1:
                    model_path = potential_files[0]
                elif len(potential_files) > 1:
                    print(f"发现多个可能的文件: {potential_files}")
                    model_path = potential_files[0]  # 使用第一个找到的文件
                    print(f"使用: {model_path}")
                else:
                    raise FileNotFoundError(f"找不到匹配的文件: {model_filename}")
            else:
                # 完整文件名
                model_path = os.path.join(model_dir, model_filename)
            
            # 获取不带扩展名的文件名
            model_name = os.path.splitext(os.path.basename(model_path))[0]
            
            return model_path, model_name
    except (ValueError, IndexError):
        pass
    
    # 默认使用car.blend
    default_model = os.path.join(model_dir, "car.blend")
    return default_model, "car"


if __name__ == "__main__":
    # 获取模型路径和名称
    model_path, model_name = get_model_path_from_args()
    print(f"渲染模型: {model_path}")
    
    # 加载3D模型
    load_3Dmodel(model_path)
    
    # 合并所有网格对象
    combined_object = combine_objects()

    # 处理模型
    if combined_object:
        # 先规范化大小
        normalize_model_size(combined_object, target_size=2.0)
        
        # 然后移动到原点
        move_bbox_to_origin(combined_object)
        
        # 设置灯光
        setup_lights()

        # 设置输出目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, "output", model_name)
        
        # 进行360度渲染
        camera_distance = 8.0  # 相机距离
        render_views(output_dir, angle_step=30, distance=camera_distance)

        # 保存最终模型
        save_combined_object(os.path.join(script_dir, "output"), model_name)
        
        print(f"模型 {model_name} 渲染完成")
    else:
        print("错误: 未能创建合并对象")