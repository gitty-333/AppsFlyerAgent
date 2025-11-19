import os
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import logging
import json
from google.api_core.exceptions import Forbidden, NotFound, BadRequest

load_dotenv()

PROJECT_ID = "practicode-2025"
BQ_LOCATION = "EU"
BQ_DATA_FILE_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")


class BQClient:
    def __init__(self):
        self.path_of_bq_data_user = BQ_DATA_FILE_PATH
        self.creds, self.sa_email, self.sa_project = self._load_bq_creds()
        self.project_id = PROJECT_ID or self.sa_project
        self.bq_client = bigquery.Client(
            location=BQ_LOCATION,
            project=self.project_id,
            credentials=self.creds
        )
        logging.info("BQ client project=%s location=%s sa_email=%s",
                     self.project_id, BQ_LOCATION, self.sa_email)

    def execute_query(self, query, query_type):
        logging.info('*********** QUERY %s START ***********', query_type)
        logging.info(query)
        try:
            job = self.bq_client.query(query)
            result = job.result()  # RowIterator
            logging.info('*********** QUERY %s DONE ***********', query_type)
            return result
        except Forbidden as e:
            raise PermissionError(
                f"BigQuery permission error for service account '{self.sa_email}' "
                f"on project '{self.project_id}'. "
                f"Ask an admin to grant at least roles/bigquery.jobUser (and dataViewer) "
                f"on project {self.project_id}. Original error: {e}"
            ) from e
        except (BadRequest, NotFound) as e:
            raise RuntimeError(f"BigQuery query failed: {e}") from e

    def _load_bq_creds(self):
        with open(self.path_of_bq_data_user, 'r') as f:
            info = json.load(f)
        creds = service_account.Credentials.from_service_account_info(info)
        sa_email = info.get("client_email")
        sa_project = info.get("project_id")
        return creds, sa_email, sa_project


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    bq_client = BQClient()
    print(bq_client.bq_client)

    qu = """
    SELECT *
    FROM `practicode-2025.clicks_data_prac.partial_encoded_clicks`
    LIMIT 10
    """
    df = bq_client.execute_query(qu, 'test_query').to_dataframe()  # add create_bqstorage_client=True later
    print(df)