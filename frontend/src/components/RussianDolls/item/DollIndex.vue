<template>
  <DollObject
    v-if="item.type === 'object'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex" />
  <DollArray
    v-else-if="item.type === 'array'"
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex" />
  <DollBase
    v-else
    :item="item"
    :schema="item.schema"
    :item-index="itemIndex" />
  <!-- <bk-form-item
      :label="item.title"
      :required="item.required"
      :property="item.property"
      :desc="item.description">
      <component
        :is="item.component"
        v-bind="item.props"
        />
    </bk-form-item> -->
</template>

<script>
import { defineComponent, toRefs } from 'vue';

export default defineComponent({
  props: {
    item: () => ({}),
    itemIndex: -1,
  },
  setup(props) {
    // console.log(props.item, props.item.type, '---------------');

    return {
      ...toRefs(props),
    };
  },
});

</script>
