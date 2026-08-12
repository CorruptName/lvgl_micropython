#include <stdbool.h>

#include "py/obj.h"
#include "py/runtime.h"
#include "esp_hosted_ota.h"

#define C6_OTA_MAX_CHUNK_SIZE (1400)

static bool c6_ota_in_progress;
static bool c6_ota_ready;

static void c6_ota_check_error(esp_err_t error) {
    if (error != ESP_OK) {
        mp_raise_OSError(error);
    }
}

static mp_obj_t c6_ota_begin(void) {
    if (c6_ota_in_progress) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("C6 OTA already in progress"));
    }

    c6_ota_check_error(esp_hosted_slave_ota_begin());
    c6_ota_in_progress = true;
    c6_ota_ready = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(c6_ota_begin_obj, c6_ota_begin);

static mp_obj_t c6_ota_write(mp_obj_t data_in) {
    if (!c6_ota_in_progress) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("C6 OTA is not in progress"));
    }

    mp_buffer_info_t data;
    mp_get_buffer_raise(data_in, &data, MP_BUFFER_READ);
    if (data.len == 0 || data.len > C6_OTA_MAX_CHUNK_SIZE) {
        mp_raise_ValueError(MP_ERROR_TEXT("OTA chunk must contain 1 to 1400 bytes"));
    }

    c6_ota_check_error(esp_hosted_slave_ota_write(data.buf, data.len));
    return mp_obj_new_int_from_uint(data.len);
}
static MP_DEFINE_CONST_FUN_OBJ_1(c6_ota_write_obj, c6_ota_write);

static mp_obj_t c6_ota_end(void) {
    if (!c6_ota_in_progress) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("C6 OTA is not in progress"));
    }

    esp_err_t error = esp_hosted_slave_ota_end();
    c6_ota_in_progress = false;
    c6_ota_ready = error == ESP_OK;
    c6_ota_check_error(error);
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(c6_ota_end_obj, c6_ota_end);

static mp_obj_t c6_ota_activate(void) {
    if (!c6_ota_ready) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("no finalized C6 OTA image"));
    }

    c6_ota_check_error(esp_hosted_slave_ota_activate());
    c6_ota_ready = false;
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(c6_ota_activate_obj, c6_ota_activate);

static const mp_rom_map_elem_t c6_ota_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_c6_ota) },
    { MP_ROM_QSTR(MP_QSTR_MAX_CHUNK_SIZE), MP_ROM_INT(C6_OTA_MAX_CHUNK_SIZE) },
    { MP_ROM_QSTR(MP_QSTR_begin), MP_ROM_PTR(&c6_ota_begin_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&c6_ota_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_end), MP_ROM_PTR(&c6_ota_end_obj) },
    { MP_ROM_QSTR(MP_QSTR_activate), MP_ROM_PTR(&c6_ota_activate_obj) },
};
static MP_DEFINE_CONST_DICT(c6_ota_globals, c6_ota_globals_table);

const mp_obj_module_t c6_ota_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&c6_ota_globals,
};

MP_REGISTER_MODULE(MP_QSTR_c6_ota, c6_ota_module);