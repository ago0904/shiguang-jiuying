Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 当前步骤: upload | mode | processing | result
    step: 'upload',
    // 已选图片路径
    selectedImage: '',
    // 已选修复模式
    selectedModes: [],
    // 进度百分比
    progress: 0,
    // 修复后图片路径
    resultImage: '',
    // 状态文字
    statusText: '正在分析照片...',
    // 模拟处理用时（秒）
    processTime: 0,
    // 模式列表
    modeList: ['colorize', 'repair', 'enhance', 'denoise'],
    // 模式名称映射
    modeNameMap: {
      colorize: '黑白上色',
      repair: '破损修复',
      enhance: '清晰度增强',
      denoise: '智能去噪'
    },
    // 定时器引用
    _progressTimer: null,
    _startTime: 0
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 如果通过URL传入mode参数，自动进入对应模式
    if (options.mode) {
      this.setData({
        selectedModes: [options.mode]
      });
    }
  },

  /**
   * 生命周期函数--监听页面卸载
   */
  onUnload() {
    this._clearProgressTimer();
  },

  /* ===== 状态1: 上传照片 ===== */

  /**
   * 选择照片
   */
  onChoosePhoto() {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        if (res.tempFiles && res.tempFiles.length > 0) {
          const tempFilePath = res.tempFiles[0].tempFilePath;
          this.setData({
            selectedImage: tempFilePath
          });
        }
      },
      fail: (err) => {
        if (err.errMsg && err.errMsg.includes('cancel')) {
          // 用户取消，不做处理
          return;
        }
        wx.showToast({
          title: '选择照片失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 进入选择模式步骤
   */
  goToModeStep() {
    if (!this.data.selectedImage) {
      wx.showToast({
        title: '请先选择照片',
        icon: 'none'
      });
      return;
    }
    this.setData({ step: 'mode' });
  },

  /* ===== 状态2: 选择模式 ===== */

  /**
   * 返回上传状态
   */
  goBackToUpload() {
    this.setData({ step: 'upload' });
  },

  /**
   * 选择/取消修复模式
   */
  onModeSelect(e) {
    const mode = e.detail.mode;
    const selectedModes = [...this.data.selectedModes];
    const index = selectedModes.indexOf(mode);

    if (index > -1) {
      // 取消选择
      selectedModes.splice(index, 1);
    } else {
      // 添加选择
      selectedModes.push(mode);
    }

    this.setData({ selectedModes });
  },

  /**
   * 开始AI修复处理
   */
  startProcessing() {
    if (this.data.selectedModes.length === 0) {
      wx.showToast({
        title: '请至少选择一种模式',
        icon: 'none'
      });
      return;
    }

    this.setData({
      step: 'processing',
      progress: 0,
      statusText: '正在分析照片...',
      _startTime: Date.now()
    });

    this._simulateProgress();
  },

  /**
   * 模拟AI处理进度
   */
  _simulateProgress() {
    this._clearProgressTimer();

    let progress = 0;
    const timer = setInterval(() => {
      // 非线性增长，模拟真实AI处理
      let increment;
      if (progress < 30) {
        increment = Math.random() * 3 + 1;
      } else if (progress < 60) {
        increment = Math.random() * 2 + 0.5;
      } else if (progress < 85) {
        increment = Math.random() * 1.5 + 0.3;
      } else {
        increment = Math.random() * 1 + 0.2;
      }

      progress += increment;

      if (progress >= 100) {
        progress = 100;
        this._clearProgressTimer();

        // 计算处理用时
        const processTime = Math.round((Date.now() - this.data._startTime) / 1000);

        // 延迟一下展示100%再切换结果
        setTimeout(() => {
          // 模拟修复结果图片（实际项目中这里应该是服务器返回的修复后图片）
          // 这里用原图作为占位，实际开发时替换为真实结果
          this.setData({
            resultImage: this.data.selectedImage,
            processTime: processTime || 3
          });
          this.setData({ step: 'result' });
        }, 500);
      }

      this._updateProgress(progress);
    }, 200);

    this.setData({ _progressTimer: timer });
  },

  /**
   * 更新进度和状态文字
   */
  _updateProgress(progress) {
    const p = Math.floor(progress);
    let statusText = '正在分析照片...';

    if (p >= 85) {
      statusText = '即将完成...';
    } else if (p >= 60) {
      statusText = '优化细节...';
    } else if (p >= 30) {
      statusText = 'AI正在修复中...';
    }

    this.setData({
      progress: p,
      statusText: statusText
    });
  },

  /**
   * 清除进度定时器
   */
  _clearProgressTimer() {
    if (this.data._progressTimer) {
      clearInterval(this.data._progressTimer);
      this.setData({ _progressTimer: null });
    }
  },

  /* ===== 状态4: 对比结果 ===== */

  /**
   * 保存到相册
   */
  saveToAlbum() {
    if (!this.data.resultImage) {
      wx.showToast({
        title: '暂无修复图片',
        icon: 'none'
      });
      return;
    }

    wx.saveImageToPhotosAlbum({
      filePath: this.data.resultImage,
      success: () => {
        wx.showToast({
          title: '保存成功',
          icon: 'success'
        });
      },
      fail: (err) => {
        if (err.errMsg && err.errMsg.includes('auth deny')) {
          wx.showModal({
            title: '需要授权',
            content: '请允许保存到相册的权限',
            success: (res) => {
              if (res.confirm) {
                wx.openSetting();
              }
            }
          });
        } else {
          wx.showToast({
            title: '保存失败',
            icon: 'none'
          });
        }
      }
    });
  },

  /**
   * 下载图片
   */
  downloadImage() {
    if (!this.data.resultImage) {
      wx.showToast({
        title: '暂无修复图片',
        icon: 'none'
      });
      return;
    }

    wx.showLoading({
      title: '下载中...',
    });

    // 如果是本地临时文件，直接使用
    if (this.data.resultImage.startsWith('wxfile://') ||
        this.data.resultImage.startsWith('http://tmp/') ||
        this.data.resultImage.startsWith('file://')) {
      wx.hideLoading();
      wx.saveImageToPhotosAlbum({
        filePath: this.data.resultImage,
        success: () => {
          wx.showToast({
            title: '下载成功',
            icon: 'success'
          });
        },
        fail: () => {
          wx.showToast({
            title: '下载失败',
            icon: 'none'
          });
        }
      });
      return;
    }

    // 网络图片需要先下载
    wx.downloadFile({
      url: this.data.resultImage,
      success: (res) => {
        wx.hideLoading();
        if (res.statusCode === 200) {
          wx.saveImageToPhotosAlbum({
            filePath: res.tempFilePath,
            success: () => {
              wx.showToast({
                title: '下载成功',
                icon: 'success'
              });
            },
            fail: () => {
              wx.showToast({
                title: '保存失败',
                icon: 'none'
              });
            }
          });
        } else {
          wx.showToast({
            title: '下载失败',
            icon: 'none'
          });
        }
      },
      fail: () => {
        wx.hideLoading();
        wx.showToast({
          title: '下载失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 重新开始
   */
  resetAll() {
    this._clearProgressTimer();
    this.setData({
      step: 'upload',
      selectedImage: '',
      selectedModes: [],
      progress: 0,
      resultImage: '',
      statusText: '',
      processTime: 0
    });
  }
});
