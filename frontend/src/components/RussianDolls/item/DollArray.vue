<template>
  <bk-form-item
    class="item-array"
    :label="item.title"
    :required="item.required"
    :property="item.property"
    :desc="item.description">
    <i v-if="!childList.length" class="array-content-add nodeman-icon nc-plus" @click.stop="() => addItem(0)" />
    <div class="array-child-group" v-else>
      <div class="array-child flex" v-for="(option, index) in childList" :key="option">
        <DollIndex
          v-for="(child, idx) in children"
          :key="`${option}_${idx}`"
          :item="child"
          :item-index="index" />
        <div class="child-btns">
          <i class="nodeman-icon nc-plus" @click.stop="() => addItem(index)" />
          <i class="nodeman-icon nc-minus" @click.stop="() => deleteItem(index)" />
        </div>
      </div>
    </div>
  </bk-form-item>
</template>

<script>
import { defineComponent, inject, ref, toRefs } from 'vue';
import { formatSchema, uuid } from '../create';

export default defineComponent({
  props: {
    item: () => ({}),
    schema: () => ({}),
  },
  setup(props) {
    const updateFormData = inject('updateFormData');

    const itemType = ref(props.item.children?.[0]?.type || 'string');

    const children = ref([formatSchema(props.schema.items, props.item.property, props.item.level + 1)]);
    const childList = ref([]);

    const addItem = (index = 0) => {
      childList.value.splice(index + 1, 0, uuid());
      updateFormData?.(props.item, 'add', index + 1);
    };
    const deleteItem = (index = 0) => {
      childList.value.splice(index, 1);
      updateFormData?.(props.item, 'delete', index);
    };

    return {
      ...toRefs(props),

      itemType,
      children,
      childList,

      addItem,
      deleteItem,
    };
  },
});

</script>
