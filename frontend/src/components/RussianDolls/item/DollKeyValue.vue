<template>
  <bk-form-item
    class="item-key-value"
    :label="extraIndex ? '' : '标签'"
    property="add_property"
    :required="!!keyModel">
    <div class="flex">
      <div class="flex1" style="flex: 1">
        <bk-input v-model="keyModel" />
      </div>
      <div class="pl10 pr10">=</div>
      <div class="flex1" style="flex: 1">
        <bk-input v-model="valueModel" />
      </div>
      <div class="child-btns">
        <i
          class="nodeman-icon nc-plus"
          @click.stop="() => addItem(index)" />
        <i
          :class="['nodeman-icon nc-minus ', { 'disabled': disabledMinus }]"
          @click.stop="() => deleteItem(index)" />
      </div>
    </div>
  </bk-form-item>
</template>

<script>
import { defineComponent, ref, toRefs } from 'vue';

export default defineComponent({
  props: {
    item: () => ({}),
    itemIndex: -1,
    extraIndex: 0,
    disabledMinus: false,
  },
  emits: ['add', 'delete'],
  setup(props, { emit }) {
    const keyModel = ref('');
    const valueModel = ref('');
    const addItem = (index) => {
      emit('add', index);
    };
    const deleteItem = (index) => {
      if (!props.disabledMinus) {
        emit('delete', index);
      }
    };

    return {
      ...toRefs(props),

      keyModel,
      valueModel,
      addItem,
      deleteItem,
    };
  },
});
</script>
