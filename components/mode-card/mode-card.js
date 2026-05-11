Component({
  /**
   * 组件的属性列表
   */
  properties: {
    mode: {
      type: String,
      value: 'colorize'
    },
    selected: {
      type: Boolean,
      value: false
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    modeMap: {
      colorize: { name: '黑白上色', icon: '🎨', color: '#C47B5A', desc: '赋予自然色彩' },
      repair: { name: '破损修复', icon: '🔧', color: '#7A9E7E', desc: '智能填补破损' },
      enhance: { name: '清晰度增强', icon: '✨', color: '#D4A35A', desc: '模糊变清晰' },
      denoise: { name: '智能去噪', icon: '🌿', color: '#7E8FA3', desc: '去除噪点' }
    }
  },

  /**
   * 计算属性
   */
  lifetimes: {
    attached() {
      const modeData = this.data.modeMap[this.properties.mode] || this.data.modeMap.colorize;
      this.setData({ modeData });
    }
  },

  observers: {
    'mode': function(newMode) {
      const modeData = this.data.modeMap[newMode] || this.data.modeMap.colorize;
      this.setData({ modeData });
    }
  },

  /**
   * 组件的方法列表
   */
  methods: {
    onTap() {
      this.triggerEvent('select', { mode: this.properties.mode });
    }
  }
});
