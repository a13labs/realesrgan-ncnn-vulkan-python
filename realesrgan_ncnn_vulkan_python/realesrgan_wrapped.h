#ifndef REALESRGAN_NCNN_VULKAN_REALESRGANWRAPPER_H
#define REALESRGAN_NCNN_VULKAN_REALESRGANWRAPPER_H
#include "realesrgan.h"

// wrapper class of ncnn::Mat
typedef struct Image {
  unsigned char *data;
  int w;
  int h;
  int elempack;
  Image(unsigned char *d, int w, int h, int channels) {
    this->data = d;
    this->w = w;
    this->h = h;
    this->elempack = channels;
  }

} Image;

union StringType {
  std::string *str;
  std::wstring *wstr;
};

class RealESRGANWrapped : public RealESRGAN {
public:
  RealESRGANWrapped(int gpuid, bool _tta_mode, int scale, int tilesize, int prepadding);
  int load(const StringType &parampath, const StringType &modelpath);
  int process(const Image &inimage, Image &outimage);
  void set_scale(int scale) { this->scale = scale;}
  void set_tile_size(int tile_size) { this->tilesize = tile_size;}
  void set_prepadding(int prepadding) { this->prepadding = prepadding;}
  int get_scale(int scale) { return this->scale; }
  int get_tile_size(int tile_size) { return this->tilesize; }
  int get_prepadding(int prepadding) { return this->prepadding; }
};

int get_gpu_count();
int get_heap_budget(int device_index);
#endif // REALESRGAN_NCNN_VULKAN_REALESRGANWRAPPER_H
