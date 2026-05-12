Component({
  /**
   * 组件的属性列表
   */
  properties: {
    originalImage: {
      type: String,
      value: ''
    },
    resultImage: {
      type: String,
      value: ''
    },
    sliderPosition: {
      type: Number,
      value: 50
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    isDragging: false,
    lastPosition: 50
  },

  /**
   * 组件的方法列表
   */
  methods: {
    onTouchStart(e) {
      this.setData({ isDragging: true });
    },

    onTouchMove(e) {
      if (!this.data.isDragging) return;

      const touch = e.touches[0];
      const query = this.createSelectorQuery();
      query.select('.compare-slider').boundingClientRect();
      query.exec((res) => {
        if (!res || !res[0]) return;
        const rect = res[0];
        let newPosition = ((touch.clientX - rect.left) / rect.width) * 100;
        // 限制在0-100范围内
        newPosition = Math.max(0, Math.min(100, newPosition));
        this.setData({ sliderPosition: newPosition });
      });
    },

    onTouchEnd(e) {
      this.setData({ isDragging: false });
    }
  }
});
