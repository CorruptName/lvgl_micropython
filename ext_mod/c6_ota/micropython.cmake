if(CONFIG_ESP_HOSTED_ENABLED)
    add_library(usermod_c6_ota INTERFACE)

    target_sources(usermod_c6_ota INTERFACE
        ${CMAKE_CURRENT_LIST_DIR}/c6_ota.c
    )

    idf_component_get_property(ESP_HOSTED_INCLUDES espressif__esp_hosted INCLUDE_DIRS)
    idf_component_get_property(ESP_HOSTED_DIR espressif__esp_hosted COMPONENT_DIR)
    list(TRANSFORM ESP_HOSTED_INCLUDES PREPEND ${ESP_HOSTED_DIR}/)
    target_include_directories(usermod_c6_ota INTERFACE ${ESP_HOSTED_INCLUDES})

    target_link_libraries(usermod INTERFACE usermod_c6_ota)
endif()