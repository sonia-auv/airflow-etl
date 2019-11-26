
if [ ${BUILD} != "local"  ]; then
    gcloud auth activate-service-account ${GCLOUD_SERVICE_ACCOUNT_EMAIL} --key-file=${AIRFLOW_HOME}/gcloud_service_account.json
fi
