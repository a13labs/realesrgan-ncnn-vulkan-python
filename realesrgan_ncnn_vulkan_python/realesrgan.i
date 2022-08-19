%module realesrgan_ncnn_vulkan_wrapper

%include "cpointer.i"
%include "carrays.i"
%include "std_string.i"
%include "std_wstring.i"
%include "stdint.i"
%include "pybuffer.i"

%pybuffer_mutable_string(unsigned char *d);
%pointer_functions(std::string, str_p);
%pointer_functions(std::wstring, wstr_p);

%{
    #include "realesrgan.h"
    #include "realesrgan_wrapped.h"
%}

class RealESRGAN
{
  public:
    RealESRGAN(int gpuid, bool tta_mode = false);
    ~RealESRGAN();
};

%include "realesrgan_wrapped.h"
