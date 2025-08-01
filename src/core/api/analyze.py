"""Analyze API endpoints."""

import io
from flask import request, jsonify, send_file
from flask_restful import Resource

from managers import asset_manager, auth_manager, log_manager
from managers.log_manager import logger
from managers.sse_manager import sse_manager
from managers.auth_manager import auth_required, ACLCheck
from model.attribute import AttributeEnum
from model.report_item import ReportItem, ReportItemAttribute
from model.news_item import NewsItemAggregate
from model.report_item_type import ReportItemType, AttributeGroupItem
from model.permission import Permission

from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate  # SystemMessagePromptTemplate, PromptTemplate
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain.chains.combine_documents import create_stuff_documents_chain


class ReportItemTypes(Resource):
    """Report item types API endpoint."""

    @auth_required("ANALYZE_ACCESS")
    def get(self):
        """Get all report item types.

        Returns:
            (dict): all report item types
        """
        return ReportItemType.get_all_json(None, auth_manager.get_user_from_jwt(), True)


class ReportItemGroups(Resource):
    """Report item groups API endpoint."""

    @auth_required("ANALYZE_ACCESS")
    def get(self):
        """Get all report item groups.

        Returns:
            (dict): all report item groups
        """
        return ReportItem.get_groups()


class ReportItems(Resource):
    """Report items API endpoint."""

    @auth_required("ANALYZE_ACCESS")
    def get(self):
        """Get all report items.

        Returns:
            (dict): all report items
        """
        try:
            filter = {}
            if "search" in request.args and request.args["search"]:
                filter["search"] = request.args["search"]
            if "completed" in request.args and request.args["completed"]:
                filter["completed"] = request.args["completed"]
            if "incompleted" in request.args and request.args["incompleted"]:
                filter["incompleted"] = request.args["incompleted"]
            if "range" in request.args and request.args["range"]:
                filter["range"] = request.args["range"]
            if "sort" in request.args and request.args["sort"]:
                filter["sort"] = request.args["sort"]

            group = None
            if "group" in request.args and request.args["group"]:
                group = request.args["group"]

            offset = None
            if "offset" in request.args and request.args["offset"]:
                offset = int(request.args["offset"])

            limit = 50
            if "limit" in request.args and request.args["limit"]:
                limit = min(int(request.args["limit"]), 200)
        except Exception as ex:
            msg = "Get ReportItems failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400

        return ReportItem.get_json(group, filter, offset, limit, auth_manager.get_user_from_jwt())

    @auth_required("ANALYZE_CREATE")
    def post(self):
        """Add a new report item.

        Returns:
            new_report_item.id (int): new report item ID
            status (int): status code
        """
        new_report_item, status = ReportItem.add_report_item(request.json, auth_manager.get_user_from_jwt())
        if status == 200:
            asset_manager.report_item_changed(new_report_item)
            sse_manager.remote_access_report_items_updated(new_report_item.report_item_type_id)
            sse_manager.report_items_updated()

        return new_report_item.id, status


class ReportItemResource(Resource):
    """Report item API endpoint."""

    @auth_required("ANALYZE_ACCESS", ACLCheck.REPORT_ITEM_ACCESS)
    def get(self, report_item_id):
        """Get a report item.

        Args:
            report_item_id (int): report item ID
        Returns:
            (dict): report item details
        """
        return ReportItem.get_detail_json(report_item_id)

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id):
        """Update a report item.

        Args:
            report_item_id (int): report item ID
        Returns:
            data (dict): updated report item details
        """
        modified, data = ReportItem.update_report_item(report_item_id, request.json, auth_manager.get_user_from_jwt())
        if modified is True:
            updated_report_item = ReportItem.find(report_item_id)
            asset_manager.report_item_changed(updated_report_item)
            sse_manager.report_item_updated(data)
            sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)

        return data

    @auth_required("ANALYZE_DELETE", ACLCheck.REPORT_ITEM_MODIFY)
    def delete(self, report_item_id):
        """Delete a report item.

        Args:
            report_item_id (int): report item ID
        Returns:
            result (bool): True if the report item was deleted successfully
            code (int): status code
        """
        result, code = ReportItem.delete_report_item(report_item_id)
        if code == 200:
            sse_manager.report_items_updated()

        return result, code


class ReportItemData(Resource):
    """Report item data API endpoint."""

    @auth_required("ANALYZE_ACCESS")
    def get(self, report_item_id):
        """Get updated report item data.

        Args:
            report_item_id (int): report item ID
        Returns:
            (dict): updated report item data
        """
        try:
            data = {}
            if "update" in request.args and request.args["update"]:
                data["update"] = request.args["update"]
            if "add" in request.args and request.args["add"]:
                data["add"] = request.args["add"]
            if "title" in request.args and request.args["title"]:
                data["title"] = request.args["title"]
            if "title_prefix" in request.args and request.args["title_prefix"]:
                data["title_prefix"] = request.args["title_prefix"]
            if "completed" in request.args and request.args["completed"]:
                data["completed"] = request.args["completed"]
            if "attribute_id" in request.args and request.args["attribute_id"]:
                data["attribute_id"] = request.args["attribute_id"]
            if "aggregate_ids" in request.args and request.args["aggregate_ids"]:
                data["aggregate_ids"] = request.args["aggregate_ids"].split("--")
            if "remote_report_item_ids" in request.args and request.args["remote_report_item_ids"]:
                data["remote_report_item_ids"] = request.args["remote_report_item_ids"].split("--")
        except Exception as ex:
            msg = "Get ReportItemData failed"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400

        user = auth_manager.get_user_from_jwt()
        if auth_manager.check_acl(report_item_id, ACLCheck.REPORT_ITEM_ACCESS, user) is False:
            msg = "ACL check failed"
            logger.warning(msg)
            return {"error": msg}, 401

        return ReportItem.get_updated_data(report_item_id, data)


class ReportItemLocks(Resource):
    """Report item locks API endpoint."""

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def get(self, report_item_id):
        """Get report item locks.

        Args:
            report_item_id (int): report item ID
        Returns:
            (dict): report item locks
        """
        if id in sse_manager.report_item_locks:
            return jsonify(sse_manager.report_item_locks[report_item_id])
        else:
            return "{}"


class ReportItemLock(Resource):
    """Report item lock API endpoint."""

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id, field_id):
        """Lock a report item field.

        Args:
            report_item_id (int): report item ID
            field_id (str): field ID
        Returns:
            (dict): report item locks
        """
        sse_manager.report_item_lock(report_item_id, field_id, auth_manager.get_user_from_jwt().id)


class ReportItemUnlock(Resource):
    """Report item unlock API endpoint."""

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id, field_id):
        """Unlock a report item field.

        Args:
            report_item_id (int): report item ID
            field_id (str): field ID
        Returns:
            (dict): report item locks
        """
        sse_manager.report_item_unlock(report_item_id, field_id, auth_manager.get_user_from_jwt().id)


class ReportItemHoldLock(Resource):
    """Report item hold lock API endpoint."""

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def put(self, report_item_id, field_id):
        """Hold a report item lock.

        Args:
            report_item_id (int): report item ID
            field_id (str): field ID
        Returns:
            (dict): report item locks
        """
        sse_manager.report_item_hold_lock(report_item_id, field_id, auth_manager.get_user_from_jwt().id)


class ReportItemAttributeEnums(Resource):
    """Report item attribute enums API endpoint."""

    @auth_required("ANALYZE_ACCESS")
    def get(self, attribute_id):
        """Get report item attribute enums.

        Args:
            attribute_id (int): attribute ID
        Returns:
            (dict): report item attribute enums
        """
        search = None
        offset = 0
        limit = 10
        if "search" in request.args and request.args["search"]:
            search = request.args["search"]
        if "offset" in request.args and request.args["offset"]:
            offset = request.args["offset"]
        if "limit" in request.args and request.args["limit"]:
            limit = request.args["limit"]
        return AttributeEnum.get_for_attribute_json(attribute_id, search, offset, limit)


class ReportItemAddAttachment(Resource):
    """Add a report item attachment."""

    @auth_required(["ANALYZE_CREATE", "ANALYZE_UPDATE"], ACLCheck.REPORT_ITEM_MODIFY)
    def post(self, report_item_id):
        """Add a report item attachment.

        Args:
            report_item_id (int): report item ID
        Returns:
            data (dict): updated report item details
        """
        file = request.files.get("file")
        if file:
            user = auth_manager.get_user_from_jwt()
            attribute_group_item_id = request.form["attribute_group_item_id"]
            description = request.form["description"]
            data = ReportItem.add_attachment(report_item_id, attribute_group_item_id, user, file, description)
            updated_report_item = ReportItem.find(report_item_id)
            asset_manager.report_item_changed(updated_report_item)
            sse_manager.report_item_updated(data)
            sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)

            return data


class ReportItemRemoveAttachment(Resource):
    """Remove a report item attachment."""

    @auth_required("ANALYZE_UPDATE", ACLCheck.REPORT_ITEM_MODIFY)
    def delete(self, report_item_id, attribute_id):
        """Remove a report item attachment.

        Args:
            report_item_id (int): report item ID
            attribute_id (int): attribute ID
        Returns:
            (dict): updated report item details
        """
        user = auth_manager.get_user_from_jwt()
        data = ReportItem.remove_attachment(report_item_id, attribute_id, user)
        updated_report_item = ReportItem.find(report_item_id)
        asset_manager.report_item_changed(updated_report_item)
        sse_manager.report_item_updated(data)
        sse_manager.remote_access_report_items_updated(updated_report_item.report_item_type_id)


class ReportItemDownloadAttachment(Resource):
    """Download a report item attachment."""

    def get(self, report_item_id, attribute_id):
        """Download a report item attachment.

        Args:
            report_item_id (int): report item ID
            attribute_id (int): attribute ID
        Returns:
            (file): report item attachment
        """
        if "jwt" in request.args:
            user = auth_manager.decode_user_from_jwt(request.args["jwt"])
            if user is not None:
                permissions = user.get_permissions()
                if "ANALYZE_ACCESS" in permissions:
                    report_item_attribute = ReportItemAttribute.find(attribute_id)
                    if (
                        report_item_attribute is not None
                        and report_item_attribute.report_item.id == report_item_id
                        and ReportItem.allowed_with_acl(report_item_attribute.report_item.id, user, False, True, False)
                    ):
                        log_manager.store_user_activity(user, "ANALYZE_ACCESS", str({"file": report_item_attribute.value}))

                        return send_file(
                            io.BytesIO(report_item_attribute.binary_data),
                            download_name=report_item_attribute.value,
                            mimetype=report_item_attribute.binary_mime_type,
                            as_attachment=True,
                        )
                    else:
                        log_manager.store_auth_error_activity("Unauthorized access attempt to Report Item Attribute")
                else:
                    log_manager.store_auth_error_activity("Insufficient permissions")
            else:
                log_manager.store_auth_error_activity("Invalid JWT")
        else:
            log_manager.store_auth_error_activity("Missing JWT")


class ReportItemLlmGenerate(Resource):
    """Report item types API endpoint."""

    @auth_required(["ANALYZE_CREATE", "ANALYZE_UPDATE"])
    def post(self, attribute_id):
        """Generate an AI overview."""
        try:
            news_item_agreggate_ids = request.json.get("news_item_agreggate_ids")
            attr = AttributeGroupItem.find(attribute_id)
            ai_prompt = attr.ai_prompt
            ai_provider = attr.ai_provider
            if not ai_provider or not ai_prompt:
                return {"message": f"Unknown AI model or empty AI prompt! (Attribute ID: {attribute_id})"}

            documents_for_llm = []
            document_nr = 0

            for agreggate_id in news_item_agreggate_ids:
                aggregate = NewsItemAggregate.find(agreggate_id)
                for news_item in aggregate.news_items:
                    document_nr += 1
                    text = f"--- START PAGE {document_nr} ---\n"
                    text += f"Title: {news_item.news_item_data.title}\n"
                    text += f"Source: {news_item.news_item_data.source}\n"
                    text += f"Link: {news_item.news_item_data.link}\n"
                    text += f"Author: {news_item.news_item_data.author}\n"
                    text += f"Language: {news_item.news_item_data.language}\n"
                    text += f"Collected: {news_item.news_item_data.collected}\n"
                    text += f"Body:\n{news_item.news_item_data.content}\n"
                    text += f"--- END PAGE {document_nr} ---\n\n"
                    documents_for_llm.append(Document(page_content=text, metadata={"page": document_nr}))

            if not documents_for_llm:
                msg = f"LLM generate: No news items to process (Report ID: {news_item_agreggate_ids})"
                logger.debug(msg)
                # return {"message": msg}, 400

            if ai_provider.api_type == "openai":
                llm = ChatOpenAI(model_name=ai_provider.model, api_key=ai_provider.api_key, base_url=ai_provider.api_url)
            else:
                msg = f"LLM generate: unsupported local model type '{ai_provider.api_type}'"
                logger.warning(msg)
                return {"message": msg}, 400

            text = (
                "The USER-TASK is refering to data in CONTEXT-DOCUMENT. "
                "You must fulfill the USER-TASK using CONTEXT-DOCUMENT and nothing else. "
                "Do not add any introduction or summary unless explicitly asked in USER-TASK.\n\n"
                "### USER-TASK\n\n{question}\n"
                "### CONTEXT-DOCUMENT\n\n"
                "{context}\n"
                "### ANSWER\n"
            )
            # tweaking prompt doesn't matter that much as using good model (good model -> better understanding what you want from him)
            # TODO: test and keep only the best prompt (delete old one)
            text = (
                "You are a data analyst AI assistant. Your task is to carefully analyze the provided User data and answer the User question "
                "based on that data. Follow these steps strictly:\n"
                "1. Read and understand the User question.\n"
                "2. Carefully review the attached User data.\n"
                "3. Identify relevant patterns, structures, anomalies, or relationships within the User data.\n"
                "4. Provide a clear, concise, and data-supported answer to the User question.\n"
                "5. Do not add any introduction or summary unless explicitly asked in User question.\n"
                "6. Only rely on the given User data for your answer. Do not invent or assume anything outside the scope of the User data.\n"
                "---\n"
                "User question:\n"
                "{question}\n"
                "---\n"
                "User data:\n"
                "{context}\n"
            )

            prompt_template = [HumanMessagePromptTemplate.from_template(text)]
            logger.debug(
                f"_____ LLM prompt ({ai_provider.model}): _____\n"
                + text.replace("{question}", ai_prompt).replace("{context}", "".join(doc.page_content for doc in documents_for_llm))
                + "_______________________"
            )

            # prompt = PromptTemplate.from_template(prompt_template)
            prompt = ChatPromptTemplate.from_messages(prompt_template)
            llm_chain = create_stuff_documents_chain(llm, prompt, document_variable_name="context")
            try:
                result = llm_chain.invoke({"context": documents_for_llm, "question": ai_prompt})
            except Exception as ex:
                msg = f"Connect to LLM failed: {ex}"
                logger.error(msg)
                return {"error": msg}, 400

            logger.debug(f"_____ LLM output: _____\n{result}\n_______________________")
            return {"message": result}

        except Exception as ex:
            msg = "LLM prompt construction failed (see logs)"
            logger.exception(f"{msg}: {ex}")
            return {"error": msg}, 400


def initialize(api):
    """Initialize API endpoints.

    Args:
        api (flask_rest): an instance of flask_rest
    """
    api.add_resource(ReportItemTypes, "/api/v1/analyze/report-item-types")
    api.add_resource(ReportItemGroups, "/api/v1/analyze/report-item-groups")
    api.add_resource(ReportItems, "/api/v1/analyze/report-items")
    api.add_resource(ReportItemResource, "/api/v1/analyze/report-items/<int:report_item_id>")
    api.add_resource(ReportItemData, "/api/v1/analyze/report-items/<int:report_item_id>/data")
    api.add_resource(ReportItemLocks, "/api/v1/analyze/report-items/<int:report_item_id>/field-locks")
    api.add_resource(ReportItemLock, "/api/v1/analyze/report-items/<int:report_item_id>/field-locks/<field_id>/lock")
    api.add_resource(ReportItemUnlock, "/api/v1/analyze/report-items/<int:report_item_id>/field-locks/<field_id>/unlock")
    api.add_resource(ReportItemHoldLock, "/api/v1/analyze/report-items/<int:report_item_id>/field-locks/<field_id>/hold")
    api.add_resource(ReportItemAttributeEnums, "/api/v1/analyze/report-item-attributes/<int:attribute_id>/enums")
    api.add_resource(ReportItemAddAttachment, "/api/v1/analyze/report-items/<int:report_item_id>/file-attributes")
    api.add_resource(ReportItemRemoveAttachment, "/api/v1/analyze/report-items/<int:report_item_id>/file-attributes/<int:attribute_id>")
    api.add_resource(
        ReportItemDownloadAttachment, "/api/v1/analyze/report-items/<int:report_item_id>/file-attributes/<int:attribute_id>/file"
    )
    api.add_resource(ReportItemLlmGenerate, "/api/v1/analyze/report-item-attributes/<int:attribute_id>/llm-generate")

    Permission.add("ANALYZE_ACCESS", "Analyze access", "Access to Analyze module")
    Permission.add("ANALYZE_CREATE", "Analyze create", "Create report item")
    Permission.add("ANALYZE_UPDATE", "Analyze update", "Update report item")
    Permission.add("ANALYZE_DELETE", "Analyze delete", "Delete report item")
