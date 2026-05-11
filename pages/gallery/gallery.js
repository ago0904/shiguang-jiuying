// 画廊页逻辑
const app = getApp()

Page({
  data: {
    galleryList: [],
    activeFilter: 'all',
    filters: [
      { key: 'all', label: '全部' },
      { key: 'colorize', label: '黑白上色' },
      { key: 'repair', label: '破损修复' },
      { key: 'enhance', label: '清晰度增强' },
      { key: 'denoise', label: '智能去噪' }
    ]
  },

  onLoad() {
    this.loadGalleryData()
  },

  onShow() {
    this.loadGalleryData()
  },

  // 加载画廊数据
  loadGalleryData() {
    const galleryData = app.globalData.galleryData || []
    // 补充模式标签显示文本
    const modeLabelMap = {
      colorize: '黑白上色',
      repair: '破损修复',
      enhance: '清晰度增强',
      denoise: '智能去噪'
    }
    const galleryList = galleryData.map(item => ({
      ...item,
      modeLabel: modeLabelMap[item.mode] || item.mode
    }))
    this.setData({ galleryList })
  },

  // 切换筛选条件
  onFilterTap(e) {
    const key = e.currentTarget.dataset.key
    this.setData({ activeFilter: key })
  },

  // 预览大图
  onPreviewImage(e) {
    const index = e.currentTarget.dataset.index
    const filteredList = this.data.galleryList.filter(item => {
      if (this.data.activeFilter === 'all') return true
      return item.mode === this.data.activeFilter
    })
    const urls = filteredList.map(item => item.image)
    const current = filteredList[index].image
    wx.previewImage({
      current,
      urls
    })
  },

  // 获取过滤后的列表（供wxml使用）
  get getFilteredList() {
    const { galleryList, activeFilter } = this.data
    if (activeFilter === 'all') return galleryList
    return galleryList.filter(item => item.mode === activeFilter)
  }
})
