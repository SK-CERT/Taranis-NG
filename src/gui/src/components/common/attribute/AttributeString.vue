<template>
    <AttributeItemLayout :add_button="addButtonVisible"
                         @add-value="add()"
                         :values="values">
        <template v-slot:content>
            <v-row v-for="(value, index) in values" :key="value.index"
                   class="valueHolder">
                <span v-if="read_only || values[index].remote" class="numbered-string-value">
                    <span v-if="values.length > 1" class="string-number text--disabled">{{ index + 1 }}.</span>
                    <span class="string-content">{{values[index].value}}</span>
                </span>
                <AttributeValueLayout v-if="!read_only && canModify && !values[index].remote"
                                      :del_button="delButtonVisible"
                                      @del-value="del(index)"
                                      :occurrence="attribute_group.min_occurrence"
                                      :values="values"
                                      :val_index="index">
                    <template v-slot:col_left>
                        <span v-if="values.length > 1" class="string-number text--disabled">{{ index + 1 }}.</span>
                    </template>
                    <template v-slot:col_middle>
                        <v-text-field v-if="!read_only && !values[index].remote"
                                      v-model="values[index].value" dense
                                      :label="$t('attribute.value')"
                                      @focus="onFocus(index)" @blur="onBlur(index)" @keyup="onKeyUp(index)"
                                      :class="getLockedStyle(index)"
                                      :disabled="values[index].locked || !canModify">
                        </v-text-field>
                    </template>
                </AttributeValueLayout>
            </v-row>
        </template>
    </AttributeItemLayout>

</template>

<script>
    import AttributesMixin from "@/components/common/attribute/attributes_mixin";
    import AttributeItemLayout from "../../layouts/AttributeItemLayout";
    import AttributeValueLayout from "../../layouts/AttributeValueLayout";

    export default {
        name: "AttributeString",
        props: {
            attribute_group: Object
        },
        components: {
            AttributeItemLayout,
            AttributeValueLayout
        },
        mixins: [AttributesMixin]
    }
</script>

<style scoped>
    .string-number {
        margin-right: 8px;
        user-select: none;
        min-width: 24px;
        display: inline-block;
    }

    .numbered-string-value {
        display: flex;
        align-items: center;
        width: 100%;
    }

    .string-content {
        flex: 1;
        word-break: break-word;
    }
</style>
