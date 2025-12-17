import streamlit as st
import cv2
import numpy as np
import time
from PIL import Image
import io
from phos.config import get_preset, PRESETS
from phos.core import FilmRenderer, standardize
from phos.utils import load_raw_image, extract_thumbnail_from_raw

version = 'v1.1.5'
# 设置页面配置 
st.set_page_config(
    page_title="Phos 胶片模拟 (" + version + ")",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def process_image(uploaded_file, preset_name, iso, tone_style, exposure_ev, halation_intensity, min_size, use_embed):
    start_time = time.time()

    # Determine file type
    filename = uploaded_file.name.lower()
    is_raw = any(filename.endswith(ext) for ext in ["dng", "arw", "cr2", "cr3", "nef", "raf", "3fr"])

    if is_raw:
        with st.spinner('正在显影 RAW 底片...'):
            # Load Raw (Returns RGB)
            # Need to seek 0 because st.file_uploader might have been read partly or just to be safe
            uploaded_file.seek(0)
            # file_bytes = io.BytesIO(uploaded_file)
            # raw_file_bytes = io.BytesIO(uploaded_file)
            raw_bytes = uploaded_file.read()    # 一次性读取字节
            # 创建两个独立的 BytesIO 对象
            uploaded_file_io = io.BytesIO(raw_bytes)  # 给 load_raw_image 使用
            raw_file_bytes_io = io.BytesIO(raw_bytes)  # 给 extract_thumbnail_from_raw 使用

            # thumbnail_image = None
            with st.spinner('正在从RAW文件中提取缩略图...'):
                thumbnail_image = extract_thumbnail_from_raw(raw_file_bytes_io)

            image = load_raw_image(uploaded_file_io)
            if image is not None:
                # Convert RGB (from rawpy) to BGR (for opencv/phos pipeline)
                image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    else:
        # Standard Image
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if image is None:
        st.error("无法读取图像文件 (暂不支持NEF压缩RAW）。RAW读取如有异常，推荐使用Adobe DNG Converter转换为DNG再使用。")
        return None, None, 0, ""

    # 复制标准化尺寸的原始图像用于对比
    original_image = image.copy()

    # Initialize Renderer
    preset = get_preset(preset_name)
    renderer = FilmRenderer(preset)

    # Standardize
    with st.spinner('正在标准化图像尺寸...'):
        image = standardize(image, min_size)
        original_standardized = standardize(original_image, min_size)

    # Process
    with st.spinner('正在进行光化学显影 (计算光照/光晕/颗粒)...'):
        film = renderer.process(image, iso, tone_style, exposure_ev, halation_intensity)
        print("film image size:" + str(film.shape))
        print(len(film.shape))
    process_time = time.time() - start_time
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_filename = f"phos_{preset_name}_{timestamp}.jpg"

    # is raw file？
    if original_image.dtype != np.uint8:
        if use_embed and thumbnail_image is not None:
            original_display = thumbnail_image
            if film.shape[0] > film.shape[1]:#竖排翻转
                original_display = cv2.rotate(original_display, cv2.ROTATE_90_COUNTERCLOCKWISE)
            original_display = np.array(original_display)
            original_display = original_display.astype(np.uint8)
            st.info('读取到RAW嵌入图作为原始图像，使用RAW进行计算光学分析')
        else:
            original_display = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
            original_display = cv2.normalize(original_display, None, 0, 255, cv2.NORM_MINMAX)
            original_display = original_display.astype(np.uint8)
            if use_embed:
                st.warning('未读取到RAW文件嵌入图，直接计算RAW显示原始图像与计算分析')
            else:
                st.warning('不使用RAW文件嵌入图，直接计算RAW显示原始图像与计算分析')

        original_display = standardize(original_display, min_size)
        # is nomo color film
        if(2==len(film.shape)):
            original_display = np.dot(original_display[...,:3], [0.11, 0.59, 0.3]).astype(np.uint8)

    else: #is jpg/png
        # 转换图像格式用于显示
        if (2 == len(film.shape)):  # is nomo color film
            # 原始图像：BGR转gray
            original_display = cv2.cvtColor(original_standardized, cv2.COLOR_BGR2GRAY)
        else:
            # 原始图像：BGR转RGB
            original_display = cv2.cvtColor(original_standardized, cv2.COLOR_BGR2RGB)

    return original_display, film, process_time, output_filename

def main():
    # --- Sidebar ---
    with st.sidebar:
        st.title("Phos")
        st.caption("ver_" + version)
        st.text("基于计算光学的胶片模拟")

        # File Uploader
        st.divider()
        uploaded_file = st.file_uploader(
            "选择一张照片(可支持RAW文件)",
            type=["jpg", "jpeg", "png", "dng", "arw", "cr2", "cr3", "nef","raf", "3fr"],
            help="上传一张照片开始冲洗。推荐使用RAW以获得高精度的16bit管线支持 (支持 JPG, PNG, ARW, CR2, CR3, NEF, RAF, 3FR, DNG)"
        )

        # 显示选项
        st.header("📊 图像输出")
        min_size_input = st.text_input(
            "输出尺寸（短边像素）：",
            value="1000",
            help="输出图像的短边尺寸。更小的图像可以显著加快处理速度，建议使用500-1000进行尝试后再全尺寸输出。"
        )
        # 处理输入
        if str.isdigit(min_size_input):
            min_size = int(min_size_input)
        else:
            st.error("请输入数字")
            # 重置为默认值
            min_size = 1000
            # 立即重新运行以更新输入框
            st.rerun()

        comparison_mode = st.selectbox(
            "显示模式:",
            ["并排对比", "显示胶片", "混合叠加"],
            index=0,
            help="选择处理前后图像的对比方式"
        )
        use_embed = st.checkbox(
            "使用嵌入预览",
            value=True,
            help="选择RAW文件图像的显示方式：使用嵌入预览/重新计算"
        )

        # 设置选项
        st.header("🎞️ 胶片冲洗设置")

        # 胶片类型选择
        preset_names = list(PRESETS.keys())
        film_type = st.selectbox(
            "请选择胶片:",
            preset_names,
            index=0,
            help=f"选择要模拟的胶片类型。\n\n当前选择: {get_preset(preset_names[0]).description}"
        )

        # Show description of selected film
        current_preset = get_preset(film_type)
        st.info(f"**{film_type}**: {current_preset.description}")

        iso_option = st.select_slider(
            "感光度 (ISO):",
            options=[50, 100, 200, 400, 800, 1600, 3200],
            value=400,
            help="模拟胶片颗粒感。ISO 越高，颗粒越粗糙 (Granularity)。"
        )

        tone_style = st.selectbox(
            "Tone Mapping (Gamma 映射):",
            ["filmic", "reinhard"],
            format_func=lambda x: "ACES Standard (电影工业标准)" if x == "filmic" else "Reinhard (传统数码)",
            index=0
        )

        exposure_ev = st.slider(
            "曝光补偿 (EV)",
            min_value=-3.0,
            max_value=3.0,
            value=0.0,
            step=0.1,
            help="调整画面整体曝光。在处理 RAW 文件时特别有用，因为线性空间下未显影的 RAW 通常看起来较暗。"
        )

        halation_intensity = st.slider(
            "光晕强度 (Halation)",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="调整光晕的扩散强度。模拟镜头镀膜和底片抗光晕层的效果。"
        )


    # --- Main Area ---


    if uploaded_file is not None:
        result = process_image(uploaded_file, film_type, iso_option, tone_style, exposure_ev, halation_intensity,
                               min_size, use_embed)

        if result and result[0] is not None:
            original_img, film_img, p_time, out_path = result

            st.toast(f"成片显影完成! 用时 {p_time:.2f}秒")

            # 显示处理信息
            col1, col2, col3 = st.columns([2,1,1])
            with col1:
                st.metric("胶片类型", film_type)
            with col2:
                st.metric("显影时间", f"{p_time:.2f}s")
            with col3:
                st.metric("输出尺寸", f"{min_size_input}px")

            st.divider()

            # 根据选择的对比模式显示图像
            if comparison_mode == "并排对比":
                st.subheader("冲洗结果")
                col1, col2 = st.columns(2)
                with col1:
                    st.image(original_img, caption="原始图像", width='stretch')
                with col2:
                    st.image(film_img, caption="胶片模拟图像", width='stretch')

            elif comparison_mode == "混合叠加":
                st.subheader("混合强度")
                st.caption("使用滑块查看叠加处理后的变化")

                # 使用st.columns创建左右布局
                col1, col2 = st.columns(2)

                with col1:
                    st.image(original_img, caption="原始图像", width='stretch')
                with col2:
                    st.image(film_img, caption="胶片模拟", width='stretch')

                # 添加滑块来混合两个图像
                blend_ratio = st.slider(
                    "混合滑块",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.5,
                    step=0.01,
                    help="向右滑动增加处理强度"
                )

                # 创建混合图像
                blend_img = cv2.addWeighted(original_img, 1 - blend_ratio, film_img, blend_ratio, 0)

                # 显示混合图像
                st.image(blend_img,
                         caption=f"混合图像 (原始: {(1 - blend_ratio) * 100:.0f}%, 处理: {blend_ratio * 100:.0f}%)",
                         width='stretch')

            else:  # 单独显示
                st.subheader("胶片模拟结果")
                st.image(film_img, caption=f"处理完成 ({p_time:.2f}s)", width='stretch')

            # 添加下载部分
            st.divider()
            st.subheader("📥 保存图像")

            col1, col2, col3 = st.columns(3)

            with col1:
                # 下载原始图像
                original_pil = Image.fromarray(original_img)
                buf_original = io.BytesIO()
                original_pil.save(buf_original, format="JPEG", quality=95)
                byte_original = buf_original.getvalue()

                st.download_button(
                    label="📷 下载原图JPG",
                    data=byte_original,
                    file_name=f"original_{out_path}",
                    mime="image/jpeg",
                    help="下载标准化后的原始图像"
                )

            with col2:
                # 下载处理后的图像
                film_pil = Image.fromarray(film_img)
                buf_film = io.BytesIO()
                film_pil.save(buf_film, format="JPEG", quality=95)
                byte_film = buf_film.getvalue()

                st.download_button(
                    label="🎞️ 下载胶片模拟",
                    data=byte_film,
                    file_name=out_path,
                    mime="image/jpeg",
                    help="下载胶片模拟处理后的图像"
                )

            with col3:
                # 下载混合图像（如果选择的是并排对比模式）
                if comparison_mode == "混合叠加":
                    comparison_pil = Image.fromarray(blend_img)
                    buf_comparison = io.BytesIO()
                    comparison_pil.save(buf_comparison, format="JPEG", quality=95)
                    byte_comparison = buf_comparison.getvalue()

                    st.download_button(
                        label="🔄 下载混合图像",
                        data=byte_comparison,
                        file_name=f"comparison_{out_path}",
                        mime="image/jpeg",
                        help="下载自定义胶片效果强度后的混合图像"
                    )
                else:
                  st.caption("Tip：选择'混合叠加'模式可调整胶片效果的应用强度")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"暗房就绪: {film_type}")
    # 添加声明部分
    st.divider()
    st.text("所有处理在云端完成，关闭页面后图像不会在服务器保存。")
    st.caption("🤝Credits:  @LYCO6273  @Dominic Duan  @子月")
    st.caption("If this project helped you, please consider giving it a ⭐️ **Star** on GitHub! "
               "It helps more people discover this tool and motivates further development. ")
    st.caption("https://github.com/ZacharyHu0/Phos")

if __name__ == "__main__":
    main()
