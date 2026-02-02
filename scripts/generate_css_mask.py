import math
import base64

def generate_wavy_circle_path(cx, cy, base_r, wave_amp, freq, phase, num_points=360):
    path_data = []
    for i in range(num_points + 1):
        # Angle goes from 0 to 2*PI
        angle = (i / num_points) * 2 * math.pi
        
        # Calculate radius at this angle
        # r = base + amp * sin(freq * angle + phase)
        r = base_r + wave_amp * math.sin(freq * angle + phase)
        
        # Convert polar to cartesian
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        
        # SVG Path Command
        if i == 0:
            path_data.append(f"M {x:.2f} {y:.2f}")
        else:
            path_data.append(f"L {x:.2f} {y:.2f}")
    
    path_data.append("Z")
    return " ".join(path_data)

def main():
    # 1. Configuration
    CX, CY = 50, 50
    BASE_R = 40
    WAVE_AMP = 2
    FREQ = 15
    FRAMES = 5  # 0, PI/2, PI, 3PI/2, 2PI
    
    # 2. Generate Paths for Animation
    paths = []
    for i in range(FRAMES):
        phase = (i / (FRAMES - 1)) * 2 * math.pi
        d = generate_wavy_circle_path(CX, CY, BASE_R, WAVE_AMP, FREQ, phase)
        paths.append(d)
    
    path_values = "; ".join(paths)
    
    # 3. Construct SVG
    # We use a black fill because for masks, usually alpha/luminance matters. 
    # Black is opaque in 'alpha' mask mode if we interpret 'mask-mode' correctly, 
    # but strictly speaking for a mask-image, fully opaque areas (black/white depending on mode) show content.
    # Standard mask: white = visible, black = transparent.
    # But usually browser default 'mask-mode: match-source' treats alpha channel.
    # So we want 'fill="black"' which is opaque alpha (opacity 1). 
    # Let's ensure it works by using fill="black" (which has alpha 1).
    
    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path fill="black">
    <animate attributeName="d" dur="2s" repeatCount="indefinite" calcMode="linear"
             values="{path_values}" />
  </path>
</svg>'''

    # Minify slightly by removing newlines for base64
    svg_minified = svg_content.replace('\n', '')
    
    # 4. Base64 Encode
    b64_svg = base64.b64encode(svg_minified.encode('utf-8')).decode('utf-8')
    data_uri = f"data:image/svg+xml;base64,{b64_svg}"
    
    # 5. Write CSS to file
    css_template = f'''/* Wavy Circle Transition */
::view-transition-new(root) {{
  mask-image: url('{data_uri}');
  mask-repeat: no-repeat;
  mask-position: center;
  mask-size: 0 0; /* Start small */
  animation: theme-wave 1.5s ease-in-out;
  mix-blend-mode: normal;
}}

::view-transition-old(root),
::view-transition-new(root) {{
  animation: none;
  mix-blend-mode: normal;
}}

@keyframes theme-wave {{
  0% {{
    mask-size: 0px 0px;
    mask-position: 0px 0px;
  }}
  100% {{
    mask-size: 300vmax 300vmax;
    mask-position: -150vmax -150vmax;
  }}
}}
'''
    with open('generated_mask.css', 'w') as f:
        f.write(css_template)
    print("CSS written to generated_mask.css")

if __name__ == "__main__":
    main()
