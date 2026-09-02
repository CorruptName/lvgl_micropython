#include <string.h>

#include "py/runtime.h"
#include "py/obj.h"
#include "py/binary.h"
#include "esp_heap_caps.h"
#include "esp_h264_alloc.h"
#include "esp_h264_enc_single_hw.h"

typedef struct _mp_h264_encoder_obj_t {
    mp_obj_base_t base;
    esp_h264_enc_handle_t encoder;
    esp_h264_enc_param_hw_handle_t params;
    uint8_t *input_buffer;
    uint8_t *output_buffer;
    size_t frame_size;
    size_t output_buffer_size;
    esp_h264_frame_type_t last_frame_type;
    bool opened;
} mp_h264_encoder_obj_t;

enum {
    MP_H264_RAW_FMT_O_UYY_E_VYY,
    MP_H264_RAW_FMT_RGB565_LE,
    MP_H264_RAW_FMT_BGR888,
    MP_H264_RAW_FMT_VUY,
    MP_H264_RAW_FMT_UYVY,
};

extern const mp_obj_type_t mp_h264_encoder_type;

static void h264_raise_error(esp_h264_err_t error, const char *operation) {
    if (error == ESP_H264_ERR_MEM) {
        mp_raise_msg_varg(&mp_type_MemoryError, MP_ERROR_TEXT("%s failed (%d)"), operation, error);
    }
    if (error != ESP_H264_ERR_OK) {
        mp_raise_msg_varg(&mp_type_OSError, MP_ERROR_TEXT("%s failed (%d)"), operation, error);
    }
}

static void h264_encoder_release(mp_h264_encoder_obj_t *self) {
    if (self->encoder != NULL) {
        if (self->opened) {
            esp_h264_enc_close(self->encoder);
            self->opened = false;
        }
        esp_h264_enc_del(self->encoder);
        self->encoder = NULL;
        self->params = NULL;
    }
    heap_caps_free(self->input_buffer);
    heap_caps_free(self->output_buffer);
    self->input_buffer = NULL;
    self->output_buffer = NULL;
    self->output_buffer_size = 0;
}

static mp_obj_t h264_encoder_close(mp_obj_t self_in) {
    h264_encoder_release(MP_OBJ_TO_PTR(self_in));
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(h264_encoder_close_obj, h264_encoder_close);

static mp_obj_t h264_encoder_make_new(const mp_obj_type_t *type, size_t n_args,
    size_t n_kw, const mp_obj_t *all_args) {
    enum { ARG_width, ARG_height, ARG_fps, ARG_bitrate, ARG_gop, ARG_format, ARG_qp_min, ARG_qp_max };
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_width, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_height, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_fps, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 30} },
        { MP_QSTR_bitrate, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 2000000} },
        { MP_QSTR_gop, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 30} },
        { MP_QSTR_format, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = MP_H264_RAW_FMT_O_UYY_E_VYY} },
        { MP_QSTR_qp_min, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 10} },
        { MP_QSTR_qp_max, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 40} },
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_int_t width = args[ARG_width].u_int;
    mp_int_t height = args[ARG_height].u_int;
    mp_int_t fps = args[ARG_fps].u_int;
    mp_int_t bitrate = args[ARG_bitrate].u_int;
    mp_int_t gop = args[ARG_gop].u_int;
    mp_int_t qp_min = args[ARG_qp_min].u_int;
    mp_int_t qp_max = args[ARG_qp_max].u_int;
    esp_h264_raw_format_t format;

    switch (args[ARG_format].u_int) {
        case MP_H264_RAW_FMT_O_UYY_E_VYY:
            format = ESP_H264_RAW_FMT_O_UYY_E_VYY;
            break;
        case MP_H264_RAW_FMT_RGB565_LE:
            format = ESP_H264_RAW_FMT_RGB565_LE;
            break;
        case MP_H264_RAW_FMT_BGR888:
            format = ESP_H264_RAW_FMT_BGR888;
            break;
        case MP_H264_RAW_FMT_VUY:
            format = ESP_H264_RAW_FMT_VUY;
            break;
        case MP_H264_RAW_FMT_UYVY:
            format = ESP_H264_RAW_FMT_UYVY;
            break;
        default:
            mp_raise_ValueError(MP_ERROR_TEXT("unknown raw format"));
    }

    if (width < 80 || width > 1920 || height < 80 || height > 2032 ||
        (width & 15) != 0 || (height & 15) != 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("width and height must be supported multiples of 16"));
    }
    if (fps < 1 || fps > 255 || gop < 1 || gop > 255 || bitrate < 1 ||
        qp_min < 0 || qp_max > 51 || qp_min > qp_max) {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid encoder parameters"));
    }
    if (!ESP_H264_HW_IS_SUPPORTED_PIC_TYPE(format)) {
        mp_raise_ValueError(MP_ERROR_TEXT("raw format is unsupported by this ESP32-P4 revision"));
    }

    size_t pixels = (size_t)width * height;
    size_t frame_size = format == ESP_H264_RAW_FMT_O_UYY_E_VYY ? pixels + pixels / 2 :
        format == ESP_H264_RAW_FMT_RGB565_LE || format == ESP_H264_RAW_FMT_UYVY ? pixels * 2 : pixels * 3;

    mp_h264_encoder_obj_t *self = mp_obj_malloc_with_finaliser(mp_h264_encoder_obj_t, type);
    uint32_t input_buffer_size = frame_size;
    uint32_t output_buffer_size = frame_size;
    self->encoder = NULL;
    self->params = NULL;
    self->input_buffer = esp_h264_aligned_calloc(
        16, 1, frame_size, &input_buffer_size, ESP_H264_MEM_INTERNAL);
    self->output_buffer = esp_h264_aligned_calloc(
        16, 1, frame_size, &output_buffer_size, ESP_H264_MEM_INTERNAL);
    self->frame_size = frame_size;
    self->output_buffer_size = output_buffer_size;
    self->last_frame_type = ESP_H264_FRAME_TYPE_INVALID;
    self->opened = false;
    if (self->input_buffer == NULL || self->output_buffer == NULL) {
        h264_encoder_release(self);
        mp_raise_msg(&mp_type_MemoryError, MP_ERROR_TEXT("unable to allocate H.264 frame buffers"));
    }

    esp_h264_enc_cfg_hw_t config = {
        .pic_type = format,
        .gop = gop,
        .fps = fps,
        .res = {.width = width, .height = height},
        .rc = {.bitrate = bitrate, .qp_min = qp_min, .qp_max = qp_max},
    };
    esp_h264_err_t error = esp_h264_enc_hw_new(&config, &self->encoder);
    if (error == ESP_H264_ERR_OK) {
        error = esp_h264_enc_open(self->encoder);
        self->opened = error == ESP_H264_ERR_OK;
    }
    if (error == ESP_H264_ERR_OK) {
        error = esp_h264_enc_hw_get_param_hd(self->encoder, &self->params);
    }
    if (error != ESP_H264_ERR_OK) {
        h264_encoder_release(self);
        h264_raise_error(error, "encoder initialization");
    }
    return MP_OBJ_FROM_PTR(self);
}

static mp_obj_t h264_encoder_encode(size_t n_args, const mp_obj_t *args) {
    mp_h264_encoder_obj_t *self = MP_OBJ_TO_PTR(args[0]);
    if (self->encoder == NULL) {
        mp_raise_ValueError(MP_ERROR_TEXT("encoder is closed"));
    }
    mp_buffer_info_t input;
    mp_get_buffer_raise(args[1], &input, MP_BUFFER_READ);
    if (input.len != self->frame_size) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("frame must contain %u bytes"), self->frame_size);
    }
    uint32_t pts = n_args > 2 ? mp_obj_get_int(args[2]) : 0;
    memcpy(self->input_buffer, input.buf, self->frame_size);
    esp_h264_enc_in_frame_t in_frame = {
        .raw_data = {.buffer = self->input_buffer, .len = self->frame_size},
        .pts = pts,
    };
    esp_h264_enc_out_frame_t out_frame = {
        .raw_data = {.buffer = self->output_buffer, .len = self->output_buffer_size},
    };
    h264_raise_error(esp_h264_enc_process(self->encoder, &in_frame, &out_frame), "encode");
    self->last_frame_type = out_frame.frame_type;
    return mp_obj_new_bytes(self->output_buffer, out_frame.length);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(h264_encoder_encode_obj, 2, 3, h264_encoder_encode);

static mp_obj_t h264_encoder_force_idr(mp_obj_t self_in) {
    mp_h264_encoder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    if (self->params == NULL) {
        mp_raise_ValueError(MP_ERROR_TEXT("encoder is closed"));
    }
    h264_raise_error(esp_h264_enc_force_idr((esp_h264_enc_param_handle_t)self->params), "force_idr");
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(h264_encoder_force_idr_obj, h264_encoder_force_idr);

static mp_obj_t h264_encoder_last_frame_type(mp_obj_t self_in) {
    mp_h264_encoder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return MP_OBJ_NEW_SMALL_INT(self->last_frame_type);
}
static MP_DEFINE_CONST_FUN_OBJ_1(h264_encoder_last_frame_type_obj, h264_encoder_last_frame_type);

static mp_obj_t h264_encoder_last_keyframe(mp_obj_t self_in) {
    mp_h264_encoder_obj_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bool(self->last_frame_type == ESP_H264_FRAME_TYPE_IDR || self->last_frame_type == ESP_H264_FRAME_TYPE_I);
}
static MP_DEFINE_CONST_FUN_OBJ_1(h264_encoder_last_keyframe_obj, h264_encoder_last_keyframe);

static const mp_rom_map_elem_t h264_encoder_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_encode), MP_ROM_PTR(&h264_encoder_encode_obj) },
    { MP_ROM_QSTR(MP_QSTR_force_idr), MP_ROM_PTR(&h264_encoder_force_idr_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&h264_encoder_close_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&h264_encoder_close_obj) },
    { MP_ROM_QSTR(MP_QSTR_last_frame_type), MP_ROM_PTR(&h264_encoder_last_frame_type_obj) },
    { MP_ROM_QSTR(MP_QSTR_last_keyframe), MP_ROM_PTR(&h264_encoder_last_keyframe_obj) },
};
static MP_DEFINE_CONST_DICT(h264_encoder_locals_dict, h264_encoder_locals_dict_table);

MP_DEFINE_CONST_OBJ_TYPE(
    mp_h264_encoder_type,
    MP_QSTR_H264Encoder,
    MP_TYPE_FLAG_NONE,
    make_new, h264_encoder_make_new,
    locals_dict, &h264_encoder_locals_dict
);

static const mp_rom_map_elem_t h264_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_h264) },
    { MP_ROM_QSTR(MP_QSTR_H264Encoder), MP_ROM_PTR(&mp_h264_encoder_type) },
    { MP_ROM_QSTR(MP_QSTR_RAW_FMT_O_UYY_E_VYY), MP_ROM_INT(MP_H264_RAW_FMT_O_UYY_E_VYY) },
    { MP_ROM_QSTR(MP_QSTR_RAW_FMT_RGB565_LE), MP_ROM_INT(MP_H264_RAW_FMT_RGB565_LE) },
    { MP_ROM_QSTR(MP_QSTR_RAW_FMT_BGR888), MP_ROM_INT(MP_H264_RAW_FMT_BGR888) },
    { MP_ROM_QSTR(MP_QSTR_RAW_FMT_VUY), MP_ROM_INT(MP_H264_RAW_FMT_VUY) },
    { MP_ROM_QSTR(MP_QSTR_RAW_FMT_UYVY), MP_ROM_INT(MP_H264_RAW_FMT_UYVY) },
    { MP_ROM_QSTR(MP_QSTR_FRAME_TYPE_IDR), MP_ROM_INT(ESP_H264_FRAME_TYPE_IDR) },
    { MP_ROM_QSTR(MP_QSTR_FRAME_TYPE_I), MP_ROM_INT(ESP_H264_FRAME_TYPE_I) },
    { MP_ROM_QSTR(MP_QSTR_FRAME_TYPE_P), MP_ROM_INT(ESP_H264_FRAME_TYPE_P) },
};
static MP_DEFINE_CONST_DICT(h264_module_globals, h264_module_globals_table);

const mp_obj_module_t h264_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&h264_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_h264, h264_module);