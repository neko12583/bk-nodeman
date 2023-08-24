<template>
  <bk-form
    class="russian-dolls-form"
    ref="russianDollsFormRef"
    v-model="formData"
    :label-width="labelWidth">
    <DollIndex :item="baseForm" :item-index="0" />
  </bk-form>
</template>

<script>
import { deepClone } from '@/common/util';
import { defineComponent, provide, ref, toRefs, watch } from 'vue';
import { initSchema } from './create';

export default defineComponent({
  name: 'RussianDollsForm',
  props: {
    data: () => [],
    layout: () => [],
    rules: () => ({}),
    labelWidth: 150,
  },
  setup(props) {
    const russianDollsFormRef = ref();
    const baseForm = ref({});
    const formatList = ref([]);
    const formData = ref({});

    const typeArr = ['object', 'array'];

    const getLastLevelData = (propItem) => {
      const { property, type } = propItem;
      const keys = property.split('.');
      // 通过类型 来确定取值是倒数第一层或第二层
      const lastIndex = typeArr.includes(type) ? keys.length : keys.length - 1;
      let lastLevelData = formData.value;
      keys.forEach((key, index) => {
        if (lastIndex > index) {
          lastLevelData = lastLevelData[key];
        }
      });
      return lastLevelData;
    };

    // type: add delete assign
    // target: index or value
    const updateFormData = (propItem, type, target) => {
      const data = getLastLevelData(propItem);
      if (type === 'assign') {
        data[propItem.prop] = target;
      } else {
        if (type === 'add') {
          const [child] = getDefaultValue(propItem);
          data.splice(target, 0, child);
        } else {
          data.splice(target, 1);
        }
      }
    };

    const getDefaultValue = (propItem, isInit) => {
      if (typeArr.includes(propItem.type)) {
        if (propItem.type === 'object') {
          return propItem.children.reduce((obj, child) => {
            obj[child.prop] = getDefaultValue(child, isInit);
            return obj;
          }, {});
        }
        return isInit ? [] : [getDefaultValue(propItem.children[0], true)];
      }
      return propItem.defaultValue;
    };

    const validate = () => russianDollsFormRef.value?.validate();
    const getFormData = () => deepClone(formData);

    provide('formData', formData);
    provide('updateFormData', updateFormData);

    watch(() => props.data, (value) => {
      const schema = initSchema(value);
      baseForm.value = schema;
      formatList.value.splice(0, formatList.value.length, ...schema.children);

      formData.value = getDefaultValue(schema, true);
    }, { immediate: true });

    return {
      ...toRefs(props),
      russianDollsFormRef,

      baseForm,
      formData,
      formatList,
      validate,
      getFormData,
    };
  },
});

</script>

<style lang="postcss">
@import "./DollForm.css";
</style>
