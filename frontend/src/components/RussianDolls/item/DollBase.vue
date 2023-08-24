<template>
  <bk-form-item
    :label="item.title"
    :required="item.required"
    :property="item.property"
    :desc="item.description">
    <component
      :is="item.component"
      v-bind="item.props"
      v-model="value"
      @change="baseValueChange"
    />
  </bk-form-item>
</template>

<script>
import { defineComponent, inject, ref, toRefs } from 'vue';

export default defineComponent({
  props: {
    item: () => ({}),
    schema: () => ({}),
    itemIndex: -1,
  },
  setup(props) {
    const updateFormData = inject('updateFormData');

    const value = ref(props.item.defaultValue);

    const baseValueChange = (value) => {
      const isNumber = props.schema.type === 'number';
      let formatValue = isNumber ? parseFloat(value) : value;

      // 调过bia 以单引号开头、结尾的值直接用作字符串
      if (!isNumber || !/^'.*'$/.test(value)) {
        try {
          formatValue = JSON.parse(value);
        } catch (err) {}
      }
      console.log(value, typeof value, formatValue, typeof formatValue);
      updateFormData?.(props.item, 'assign', formatValue);
    };

    return {
      ...toRefs(props),

      value,
      baseValueChange,
    };
  },
});
</script>
