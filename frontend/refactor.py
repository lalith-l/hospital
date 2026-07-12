import sys

with open("src/PatientChat.tsx", "r") as f:
    content = f.read()

# 1. Change layout container from md:flex-row to just flex-col
content = content.replace(
    'flex flex-col md:flex-row relative z-10 backdrop-blur-xl">',
    'flex flex-col relative z-10 backdrop-blur-xl">'
)

# 2. Extract Sidebar contents
start_marker = "      {/* Sidebar - Optional for later phases, kept minimal for now */}"
end_marker = "      {/* Main Chat Area */}"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

sidebar_content = content[start_idx:end_idx]

# 3. Extract the 3 specific panels from the sidebar content
live_priors_start = sidebar_content.find("{/* Live Priors Card */}")
stat_diffs_start = sidebar_content.find("{/* Statistical Differentials Card */}")
behav_coh_start = sidebar_content.find("{/* Behavioral Coherence Panel */}")

live_priors = sidebar_content[live_priors_start:stat_diffs_start].strip()
stat_diffs = sidebar_content[stat_diffs_start:behav_coh_start].strip()
behav_coh = sidebar_content[behav_coh_start:sidebar_content.rfind("</div>\n      </div>")].strip()

# Adjust the Behavioral Coherence closing tags
behav_coh = behav_coh.replace("            </div>\n          )}", "            </div>\n          )}")

# 4. Remove sidebar from main content
content = content[:start_idx] + content[end_idx:]

# 5. Make the Top Action Bar relative and natural (remove absolute top-0 left-0)
top_bar_start = content.find('{/* Top Action Bar Header */}')
top_bar_old = '        <div className="absolute top-0 left-0 w-full bg-[#131820] border-b border-white/10 p-3 flex justify-between items-center z-50 shadow-md">'
top_bar_new = '        <div className="w-full bg-[#131820] border-b border-white/10 p-3 flex justify-between items-center z-50 shrink-0 shadow-md">'
content = content.replace(top_bar_old, top_bar_new)

# Fix the padding on the chat container (remove pt-20)
content = content.replace(
    '<div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-6 pt-20 space-y-6 z-10 relative">',
    '<div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-6 space-y-6 z-10 relative">'
)

# 6. Insert the 3 panels at the bottom
bottom_insertion_marker = "      </div>\n    </div>\n    </div>"
bottom_insertion_idx = content.find(bottom_insertion_marker)

new_bottom_panels = """
        {/* Bottom Dashboard Panels */}
        <div className="w-full shrink-0 border-t border-white/10 bg-[#0a0d14] p-4 grid grid-cols-1 md:grid-cols-3 gap-4 h-auto md:h-[240px] overflow-y-auto custom-scrollbar z-20">
          
          <div className="h-full">
            """ + live_priors + """
          </div>

          <div className="h-full">
            """ + stat_diffs + """
          </div>

          <div className="h-full">
            """ + behav_coh + """
          </div>

        </div>
"""

content = content[:bottom_insertion_idx] + new_bottom_panels + content[bottom_insertion_idx:]

with open("src/PatientChat.tsx", "w") as f:
    f.write(content)

print("Refactoring complete.")
