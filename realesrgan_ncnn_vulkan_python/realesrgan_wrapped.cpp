#include "realesrgan_wrapped.h"

RealESRGANWrapped::RealESRGANWrapped(int gpuid, bool _tta_mode, int scale, int tilesize, int prepadding)
    : RealESRGAN(gpuid, _tta_mode) {

      this->scale = scale;
      this->tilesize = tilesize;
      this->prepadding = prepadding;
}

int RealESRGANWrapped::load(const StringType &parampath,
                      const StringType &modelpath) {
#if _WIN32
  return RealESRGAN::load(*parampath.wstr, *modelpath.wstr);
#else
  return RealESRGAN::load(*parampath.str, *modelpath.str);
#endif
}

int RealESRGANWrapped::process(const Image &inimage, Image &outimage) {
  int c = inimage.elempack;
  ncnn::Mat inimagemat =
      ncnn::Mat(inimage.w, inimage.h, (void *)inimage.data, (size_t)c, c);
  ncnn::Mat outimagemat =
      ncnn::Mat(outimage.w, outimage.h, (void *)outimage.data, (size_t)c, c);
  return RealESRGAN::process(inimagemat, outimagemat);
}
int get_gpu_count() { return ncnn::get_gpu_count(); }
int get_heap_budget(int device_index) { return ncnn::get_gpu_device()->get_heap_budget();}