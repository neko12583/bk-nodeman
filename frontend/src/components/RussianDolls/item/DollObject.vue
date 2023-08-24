<template>
  <!-- <component is> -->
  <div class="item-object">
    <DollIndex v-for="child in newSchema.children" :key="child.id" :item="child" :item-index="itemIndex" />
    <DollKeyValue
      v-for="(extra, index) in extraList"
      :key="extra"
      :class="{ 'hide-minus': h }"
      :item="newSchema"
      :item-index="itemIndex"
      :extra-index="index"
      :disabled-minus="extraList.length < 2"
      @add="() => addExtra(index + 1)"
      @delete="() => deleteExtra(index)" />
  </div>
</template>

<script>
import { defineComponent, ref, toRefs } from 'vue';
import { uuid } from '../create';
export default defineComponent({
  props: {
    item: () => ({}),
    schema: () => ({}),
    itemIndex: -1,
  },
  setup(props) {
    const { item, itemIndex } = toRefs(props);
    // console.log('---------------------', itemIndex, !!item.value.parentProp);

    // 在数组之中的时候需要矫正property
    const newProperty = ref((itemIndex.value > -1 && !!item.value.parentProp)
      ? `${item.value.parentProp}.${itemIndex.value}`
      : item.value.parentProp);

    const newSchema = ref({
      ...item.value,
      property: newProperty.value
        ? `${newProperty.value}.${itemIndex.value > -1 ? itemIndex.value : item.value.prop}`
        : item.value.prop,
      children: item.value?.children
        ? item.value.children.map(child => ({
          ...child,
          parentProp: newProperty.value,
          property: newProperty.value
            ? `${newProperty.value}.${child.prop}`
            : child.prop,
        }))
        : null,
    });

    const extraList = ref([uuid()]);

    const addExtra = (index) => {
      console.log(index);
      extraList.value.splice(index, 0, uuid());
    };
    const deleteExtra = (index) => {
      extraList.value.splice(index, 1);
    };

    return {
      itemIndex,
      newProperty,
      newSchema,
      extraList,

      addExtra,
      deleteExtra,
    };
  },
});

</script>

