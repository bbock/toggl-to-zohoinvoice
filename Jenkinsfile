pipeline {
    agent any

    stages {
        stage('Unit test') {
            steps {
                 sh 'serverless --help' // to ensure it is installed
            }
        }

        stage('Integration test') {
            steps {
                sh 'serverless deploy --stage dev'
                sh 'serverless invoke --stage dev --function hello'
            }
        }

         stage('Production') {
            steps {
                sh 'serverless deploy --stage production --region eu-west-1'
                sh 'serverless invoke --stage production --region eu-west-1 --function hello'
            }
        }

        stage('Teardown') {
            steps {
                echo 'No need for DEV environment now, tear it down'
                sh 'serverless remove --stage dev'
            }
        }

    }


    environment {
        // no I won't check them in to GitHub ;)
        AWS_ACCESS_KEY_ID = credentials('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = credentials('AWS_SECRET_ACCESS_KEY')
    }

}
