import math
import base64

def generate_wavy_circle_path(cx, cy, base_r, wave_amp, freq, phase, num_points=360):
    path_data = []
    # Loop one extra point to close perfectly although Z does it, 
    # but for animation interpolation having the same number of points is key.
    for i in range(num_points):
        angle = (i / num_points) * 2 * math.pi
        r = base_r + wave_amp * math.sin(freq * angle + phase)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        
        command = "M" if i == 0 else "L"
        path_data.append(f"{command} {x:.2f} {y:.2f}")
    
    path_data.append("Z")
    return " ".join(path_data)

def main():
    # 1. Configuration
    CX, CY = 50, 50
    BASE_R = 40
    WAVE_AMP = 3
    FREQ = 12
    # Ensure smooth loop
    FRAMES = 5
    
    # 2. Generate Paths for Animation
    paths = []
    for i in range(FRAMES):
        # 0 to 2PI
        phase = (current_frame := i) / (FRAMES - 1) * 2 * math.pi
        # Actually, since sin(x) has period 2PI, 
        # phase 0 is same as phase 2PI.
        # But for 'values' in animate, we need strict matching points.
        # The points generated are consistent in count.
        d = generate_wavy_circle_path(CX, CY, BASE_R, WAVE_AMP, FREQ, phase)
        paths.append(d)
    
    path_values = ";".join(paths)
    
    # 3. Construct SVG
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path fill="black">
    <animate attributeName="d" dur="2s" repeatCount="indefinite" calcMode="linear"
             values="{path_values}" />
  </path>
</svg>'''

    # Minify for base64
    svg_minified = svg_content.replace('\n', '')
    
    # 4. Base64 Encode
    b64_svg = base64.b64encode(svg_minified.encode('utf-8')).decode('utf-8')
    data_uri = f"data:image/svg+xml;base64,{b64_svg}"
    
    # 5. Print CSS
    css_template = f'''/* Canvas Theme Transition */
::view-transition-old(root),
::view-transition-new(root) {{
  animation: none;
  mix-blend-mode: normal;
}}

::view-transition-new(root) {{
  mask-image: url('{data_uri}');
  mask-repeat: no-repeat;
  mask-position: 0 0;
  mask-size: 0 0;
  animation: theme-wave 1s ease-in-out;
  /* Ensure the new view is on top */
  z-index: 9999;
}}

@keyframes theme-wave {{
  from {{
    mask-size: 0px 0px;
    mask-position: 0px 0px;
  }}
  to {{
    mask-size: 300vmax 300vmax;
    mask-position: -150vmax -150vmax;
  }}
}}
'''
    print(css_template)

if __name__ == "__main__":
    main()
