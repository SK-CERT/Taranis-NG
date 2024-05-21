<template>
    <!--<v-card>
        <v-card-title style="font-size: 16px; font-weight: bold; padding-top:0; padding-bottom:0">
            {{attribute_item.attribute_group_item.title}}
        </v-card-title>

        <v-card-text>
            <v-divider style="padding-bottom:8px"></v-divider>
            <component v-bind:is="attributeType()" :attribute_group="attribute_item.attribute_group_item"
                       :values="attribute_item.values"
                       :read_only="read_only" :edit="edit" :modify="modify" :report_item_id="report_item_id"></component>
        </v-card-text>
    </v-card>-->
    <component v-bind:is="attributeType()" :attribute_group="attribute_item.attribute_group_item"
               :values="attribute_item.values"
               :read_only="read_only" :edit="edit" :modify="modify" :report_item_id="report_item_id"></component>

</template>

<script>
    import AttributeString from "@/components/common/attribute/AttributeString";
    import AttributeNumber from "@/components/common/attribute/AttributeNumber";
    import AttributeRichText from "@/components/common/attribute/AttributeRichText";
    import AttributeAttachment from "@/components/common/attribute/AttributeAttachment";
    import AttributeTLP from "@/components/common/attribute/AttributeTLP";
    import AttributeText from "@/components/common/attribute/AttributeText";
    import AttributeDate from "@/components/common/attribute/AttributeDate";
    import AttributeEnum from "@/components/common/attribute/AttributeEnum";
    import AttributeRadio from "@/components/common/attribute/AttributeRadio";
    import AttributeCPE from "@/components/common/attribute/AttributeCPE";
    import AttributeCVE from "@/components/common/attribute/AttributeCVE";
    import AttributeCWE from "@/components/common/attribute/AttributeCWE";
    import AttributeBoolean from "@/components/common/attribute/AttributeBoolean";
    import AttributeTime from "@/components/common/attribute/AttributeTime";
    import AttributeDateTime from "@/components/common/attribute/AttributeDateTime";
    import AttributeCVSS from "@/components/common/attribute/AttributeCVSS";

    export default {
        name: "AttributeContainer",
        components: {
            AttributeString,
            AttributeNumber,
            AttributeText,
            AttributeRichText,
            AttributeAttachment,
            AttributeTLP,
            AttributeDate,
            AttributeEnum,
            AttributeRadio,
            AttributeCPE,
            AttributeCVE,
            AttributeCWE,
            AttributeBoolean,
            AttributeTime,
            AttributeDateTime,
            AttributeCVSS
        },
        props: {
            attribute_item: Object,
            read_only: Boolean,
            edit: Boolean,
            modify: Boolean,
            report_item_id: Number
        },
        data: () => ({
            attributes: {
                STRING: "String",
                NUMBER: "Number",
                TEXT: "Text",
                RICH_TEXT: "RichText",
                ATTACHMENT: "Attachment",
                TLP: "TLP",
                DATE: "Date",
                ENUM: "Enum",
                RADIO: "Radio",
                CPE: "CPE",
                CVE: "CVE",
                CWE: "CWE",
                BOOLEAN: "Boolean",
                TIME: "Time",
                DATE_TIME: "DateTime",
                CVSS: "CVSS"
            }
        }),
        methods: {
            attributeType: function(){
                return "Attribute" + this.attributes[this.attribute_item.attribute_group_item.attribute.type];
            }
        }
    }
</script>
