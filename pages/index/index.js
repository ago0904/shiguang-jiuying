Page({
  /**
   * 页面的初始数据
   */
  data: {
    // 四大修复模式
    modeList: [
      {
        key: 'colorize',
        name: '黑白上色',
        icon: '\u{1F3A8}',
        desc: '为黑白照片注入自然色彩',
        color: '#C47B5A',
        bgColor: '#FDF1EC'
      },
      {
        key: 'repair',
        name: '破损修复',
        icon: '\u{1F527}',
        desc: '智能填补破损与划痕',
        color: '#7A9E7E',
        bgColor: '#EDF5EE'
      },
      {
        key: 'enhance',
        name: '清晰度增强',
        icon: '\u{2728}',
        desc: '模糊照片变清晰',
        color: '#D4A35A',
        bgColor: '#FBF3E4'
      },
      {
        key: 'denoise',
        name: '智能去噪',
        icon: '\u{1F33F}',
        desc: '去除噪点保留细节',
        color: '#7E8FA3',
        bgColor: '#EEF1F4'
      }
    ],

    // 精选修复案例
    caseList: [
      {
        id: 1,
        image: '/images/gallery-1.jpg',
        title: '黑白上色',
        subtitle: '老照片重现色彩'
      },
      {
        id: 2,
        image: '/images/gallery-2.jpg',
        title: '破损修复',
        subtitle: '划痕完美消失'
      },
      {
        id: 3,
        image: '/images/gallery-3.jpg',
        title: '清晰度增强',
        subtitle: '模糊变清晰'
      }
    ],

    // 用户评价
    reviewList: [
      {
        id: 1,
        avatar: '/images/avatar-user-1.jpg',
        name: '李女士',
        rating: 5,
        content: '修复了爷爷奶奶的结婚照，效果超出预期！上色非常自然，仿佛回到了那个年代。'
      },
      {
        id: 2,
        avatar: '/images/avatar-user-2.jpg',
        name: '王先生',
        rating: 5,
        content: '孩子小时候的照片模糊了，用清晰度增强功能后，细节都回来了，非常感动。'
      },
      {
        id: 3,
        avatar: '/images/avatar-user-3.jpg',
        name: '张小姐',
        rating: 5,
        content: '破损的老照片修复得很完美，划痕和折痕都消失了，推荐给所有想保存回忆的人。'
      }
    ],

    // 页面动画状态
    showHero: false,
    showFeatures: false,
    showCases: false,
    showReviews: false,
    showCTA: false
  },

  /**
   * 生命周期函数--监听页面加载
   */
  onLoad(options) {
    // 按顺序触发各区域入场动画
    this.triggerAnimation('showHero', 100);
    this.triggerAnimation('showFeatures', 400);
    this.triggerAnimation('showCases', 700);
    this.triggerAnimation('showReviews', 1000);
    this.triggerAnimation('showCTA', 1300);
  },

  /**
   * 触发动画显示
   */
  triggerAnimation(key, delay) {
    setTimeout(() => {
      this.setData({ [key]: true });
    }, delay);
  },

  /**
   * 跳转到修复页面
   */
  navigateToRestore(e) {
    const mode = e.currentTarget.dataset.mode;
    wx.navigateTo({
      url: `/pages/restore/restore?mode=${mode}`,
      fail: () => {
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * Hero区域CTA按钮点击
   */
  onHeroCTAClick() {
    // 平滑滚动到功能区域
    wx.createSelectorQuery()
      .select('.feature-section')
      .boundingClientRect((rect) => {
        if (rect) {
          wx.pageScrollTo({
            scrollTop: rect.top,
            duration: 500
          });
        }
      })
      .exec();
  },

  /**
   * 底部CTA按钮点击
   */
  onCTAClick() {
    // 默认跳转到黑白上色模式
    wx.navigateTo({
      url: '/pages/restore/restore?mode=colorize',
      fail: () => {
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 点击向下滚动箭头
   */
  onScrollDown() {
    wx.createSelectorQuery()
      .select('.feature-section')
      .boundingClientRect((rect) => {
        if (rect) {
          wx.pageScrollTo({
            scrollTop: rect.top,
            duration: 500
          });
        }
      })
      .exec();
  },

  /**
   * 分享功能
   */
  onShareAppMessage() {
    return {
      title: '拾光旧影 - AI智能修复老照片',
      path: '/pages/index/index'
    };
  }
});
