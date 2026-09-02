add_library(usermod_h264 INTERFACE)

target_sources(usermod_h264 INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/modh264.c
)

idf_component_get_property(H264_INCLUDES espressif__esp_h264 INCLUDE_DIRS)
idf_component_get_property(H264_DIR espressif__esp_h264 COMPONENT_DIR)
list(TRANSFORM H264_INCLUDES PREPEND ${H264_DIR}/)
target_include_directories(usermod_h264 INTERFACE ${H264_INCLUDES})

target_link_libraries(usermod_h264 INTERFACE
    idf::espressif__esp_h264
)

target_link_libraries(usermod INTERFACE usermod_h264)