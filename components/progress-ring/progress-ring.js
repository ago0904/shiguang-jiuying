Component({
  /**
   * 组件的属性列表
   */
  properties: {
    progress: {
      type: Number,
      value: 0,
      observer(newVal) {
        const progress = Math.max(0, Math.min(100, newVal || 0));
        const circumference = 2 * Math.PI * 54;
        const dashOffset = circumference * (1 - progress / 100);
        this.setData({
          circumference: Math.round(circumference * 100) / 100,
          dashOffset: Math.round(dashOffset * 100) / 100
        });
      }
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    circumference: 2 * Math.PI * 54,
    dashOffset: 2 * Math.PI * 54
  },

  lifetimes: {
    attached() {
      const circumference = 2 * Math.PI * 54;
      const progress = Math.max(0, Math.min(100, this.properties.progress || 0));
      const dashOffset = circumference * (1 - progress / 100);
      this.setData({
        circumference: Math.round(circumference * 100) / 100,
        dashOffset: Math.round(dashOffset * 100) / 100
      });
    }
  }
});
