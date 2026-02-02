
def main():
    css_path = 'frontend/src/index.css'
    mask_path = 'generated_mask.css'

    with open(mask_path, 'r', encoding='utf-8') as f:
        new_css_block = f.read()

    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the block start
    start_marker = "/* Canvas Theme Transition */"
    if start_marker in content:
        # We need to replace from start_marker to the end of the file, or assume the block is at the end.
        # Based on previous read_file, it was at the end.
        # But let's be careful.
        parts = content.split(start_marker)
        if len(parts) > 1:
            # Keep everything before the marker
            pre_content = parts[0]
            # Replace the rest with new block
            new_content = pre_content + new_css_block
            
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Successfully updated {css_path}")
        else:
            print("Could not split by marker correctly.")
    else:
        # Append if not found? But user said replace.
        # If not found, maybe just append.
        print("Marker not found, appending.")
        with open(css_path, 'a', encoding='utf-8') as f:
            f.write("\n" + new_css_block)
            
if __name__ == "__main__":
    main()
