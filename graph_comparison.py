import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D

# Target Dimensions: 24.51 cm x 10.78 cm (Final output size)
target_width_in = 24.51 / 2.54
target_height_in = 11.0 / 2.54 
TARGET_FIGSIZE = (target_width_in, target_height_in)

# --- Global Style Adjustments (Magnified Text) ---
TITLE_FS = 12
LABEL_FS = 10
ANN_FS = 10
LEGEND_FS = 12

# --- Data Definition ---
data_points = [
    # NOTE: ID 5-10 corresponds to the references list
    {"plot_id": 5, "text": "Tang et al. (2010)", "sac": 1.7, "sec": 0.70, "ce": 60, "color": "black", "marker": "o"},
    {"plot_id": 6, "text": "Gaikwad (2011)", "sac": 2.9, "sec": 0.60, "ce": 65, "color": "black", "marker": "s"},
    {"plot_id": 7, "text": "Liu et al. (2019)", "sac": 13.5, "sec": 0.45, "ce": 85, "color": "blue", "marker": "^"},
    {"plot_id": 8, "text": "Zhang et al. (2021)", "sac": 15.2, "sec": 0.48, "ce": 85, "color": "blue", "marker": "^"},
    {"plot_id": 9, "text": "Pan et al. (2018)", "sac": 6.2, "sec": 0.29, "ce": 90, "color": "orange", "marker": "D"},
    {"plot_id": 10, "text": "Li et al. (2022)", "sac": 4.5, "sec": 0.35, "ce": 80, "color": "orange", "marker": "D"},
    {"plot_id": None, "text": "This Work", "sac": 1.64, "sec": 0.034, "ce": 86.7, "color": "red", "marker": "*"}
]

# Legend Elements (Static)
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='black', label='Standard AC', markersize=12),
    Line2D([0], [0], marker='D', color='w', markerfacecolor='orange', label='MCDI / Membrane', markersize=12),
    Line2D([0], [0], marker='^', color='w', markerfacecolor='blue', label='Doped / MOF-derived', markersize=12),
    Line2D([0], [0], marker='*', color='w', markerfacecolor='red', markersize=18, label='This Work')
]

# ==========================================
# Plot 2: SEC vs CE (Final Code)
# ==========================================
fig2, ax2 = plt.subplots(figsize=TARGET_FIGSIZE) 

for d in data_points:
    is_this_work = d['text'] == "This Work"
    ms_size = 22 if is_this_work else 15
    
    # Plot Marker
    ax2.plot(d['ce'], d['sec'], marker=d['marker'], color=d['color'], markersize=ms_size, linestyle='', markeredgecolor='black' if not is_this_work else 'red')
    
    # Prepare Label
    label_str = d['text'] if d['plot_id'] is None else f"[{d['plot_id']}] {d['text']}"
    
    # Position Logic (Right Horizontal)
    x_offset = 3.0
    x_txt = d['ce'] + x_offset
    y_txt = d['sec']
    ha, va = 'left', 'center'
    
    # Collision adjustment for Liu vs Zhang overlap
    if d['plot_id'] == 7: # Liu (0.45)
        y_txt -= 0.015 # Slightly Up (Visual)
    if d['plot_id'] == 8: # Zhang (0.48)
        y_txt += 0.015 # Slightly Down (Visual)
        
    font_weight = 'bold' if is_this_work else 'normal'
    # Corrected the typo: fontweight=font_weight
    ax2.text(x_txt, y_txt, label_str, ha=ha, va=va, fontsize=ANN_FS, fontweight=font_weight, color='black')

# Regions
rect_ce_low = patches.Rectangle((40, 0.4), 40, 1.2, linewidth=0, facecolor='gray', alpha=0.15, label='Typical AC Range')
rect_ce_high = patches.Rectangle((80, 0.1), 20, 0.7, linewidth=0, facecolor='blue', alpha=0.1, label='MCDI/Advanced Range')
ax2.add_patch(rect_ce_low)
ax2.add_patch(rect_ce_high)

# Settings
ax2.invert_yaxis()
ax2.set_xlabel('Charge Efficiency (CE) [%]', fontsize=LABEL_FS)
ax2.set_ylabel('Specific Energy Consumption (SEC) [kWh/m³]', fontsize=LABEL_FS)
ax2.set_title('Charge Efficiency vs Energy Consumption', fontsize=TITLE_FS)
ax2.grid(True, linestyle='--', alpha=0.5)
ax2.tick_params(axis='both', which='major', labelsize=LABEL_FS * 0.7)
ax2.set_ylim(-0.1, 0.8)
ax2.set_xlim(40, 105)

# Legend Position -> Upper Left
ax2.legend(handles=legend_elements, loc='upper left', framealpha=0.8, fontsize=LEGEND_FS)

plt.tight_layout()
plt.show()