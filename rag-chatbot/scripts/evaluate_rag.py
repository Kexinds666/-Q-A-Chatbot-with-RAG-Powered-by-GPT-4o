"""
RAGAS evaluation script for RAG quality assessment
"""

import asyncio
import json
import os
from typing import List, Dict, Any
import pandas as pd
from datasets import Dataset
import structlog

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_relevancy
)

from app.services.chat_service import ChatService
from app.services.vector_service import VectorService
from app.core.config import settings

logger = structlog.get_logger()


class RAGEvaluator:
    """RAG evaluation using RAGAS framework"""
    
    def __init__(self, chat_service: ChatService, vector_service: VectorService):
        self.chat_service = chat_service
        self.vector_service = vector_service
        self.evaluation_results = []
    
    async def create_evaluation_dataset(self) -> Dataset:
        """Create evaluation dataset with questions and ground truth"""
        
        # Sample evaluation questions and expected answers
        evaluation_data = [
            {
                "question": "What is the main topic discussed in the document?",
                "ground_truth": "The document discusses [topic] and its implications for [domain].",
                "contexts": []
            },
            {
                "question": "What are the key findings mentioned?",
                "ground_truth": "The key findings include [finding1], [finding2], and [finding3].",
                "contexts": []
            },
            {
                "question": "What recommendations are provided?",
                "ground_truth": "The document recommends [recommendation1] and [recommendation2].",
                "contexts": []
            },
            {
                "question": "How can this information be applied?",
                "ground_truth": "This information can be applied by [application1] and [application2].",
                "contexts": []
            },
            {
                "question": "What are the limitations mentioned?",
                "ground_truth": "The limitations include [limitation1] and [limitation2].",
                "contexts": []
            }
        ]
        
        # Generate contexts and answers for each question
        for item in evaluation_data:
            try:
                # Get relevant contexts using vector search
                contexts = await self.vector_service.hybrid_search(
                    query=item["question"],
                    top_k=5
                )
                
                # Generate answer using chat service
                chat_result = await self.chat_service.process_message(
                    message=item["question"],
                    session_id="evaluation"
                )
                
                # Prepare contexts for RAGAS
                item["contexts"] = [ctx["content"] for ctx in contexts]
                item["answer"] = chat_result["answer"]
                
                logger.info(f"Generated evaluation data for: {item['question'][:50]}...")
                
            except Exception as e:
                logger.error(f"Failed to generate data for question: {item['question']}", error=str(e))
                # Use empty data as fallback
                item["contexts"] = []
                item["answer"] = "Error generating answer"
        
        # Create dataset
        dataset = Dataset.from_list(evaluation_data)
        return dataset
    
    async def run_evaluation(self) -> Dict[str, Any]:
        """Run RAGAS evaluation"""
        try:
            logger.info("Starting RAGAS evaluation")
            
            # Create evaluation dataset
            dataset = await self.create_evaluation_dataset()
            
            # Define metrics to evaluate
            metrics = [
                faithfulness,      # Measures factual consistency of generated answer
                answer_relevancy,  # Measures how relevant the answer is to the question
                context_precision, # Measures precision of retrieved context
                context_recall,    # Measures recall of retrieved context
                context_relevancy  # Measures relevancy of retrieved context
            ]
            
            # Run evaluation
            logger.info("Running RAGAS evaluation metrics")
            result = evaluate(
                dataset=dataset,
                metrics=metrics,
                llm=settings.OPENAI_MODEL,
                embeddings=settings.OPENAI_EMBEDDING_MODEL
            )
            
            # Process results
            evaluation_results = {
                "overall_scores": {
                    "faithfulness": float(result["faithfulness"]),
                    "answer_relevancy": float(result["answer_relevancy"]),
                    "context_precision": float(result["context_precision"]),
                    "context_recall": float(result["context_recall"]),
                    "context_relevancy": float(result["context_relevancy"])
                },
                "detailed_results": result.to_pandas().to_dict('records'),
                "evaluation_metadata": {
                    "total_questions": len(dataset),
                    "evaluation_date": pd.Timestamp.now().isoformat(),
                    "model_used": settings.OPENAI_MODEL,
                    "embedding_model": settings.OPENAI_EMBEDDING_MODEL
                }
            }
            
            # Calculate overall score
            scores = evaluation_results["overall_scores"]
            overall_score = sum(scores.values()) / len(scores)
            evaluation_results["overall_score"] = overall_score
            
            logger.info("RAGAS evaluation completed", overall_score=overall_score)
            
            return evaluation_results
            
        except Exception as e:
            logger.error("RAGAS evaluation failed", error=str(e))
            raise
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save evaluation results to file"""
        if filename is None:
            filename = f"rag_evaluation_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join("evaluation_results", filename)
        os.makedirs("evaluation_results", exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info("Evaluation results saved", filepath=filepath)
        return filepath
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable evaluation report"""
        scores = results["overall_scores"]
        overall = results["overall_score"]
        
        report = f"""
RAG System Evaluation Report
============================

Overall Score: {overall:.3f}/1.0

Detailed Metrics:
-----------------
Faithfulness: {scores['faithfulness']:.3f} - Measures factual consistency
Answer Relevancy: {scores['answer_relevancy']:.3f} - Measures answer relevance to question
Context Precision: {scores['context_precision']:.3f} - Measures precision of retrieved context
Context Recall: {scores['context_recall']:.3f} - Measures recall of retrieved context
Context Relevancy: {scores['context_relevancy']:.3f} - Measures relevancy of retrieved context

Interpretation:
---------------
- Scores above 0.8: Excellent performance
- Scores 0.6-0.8: Good performance
- Scores 0.4-0.6: Fair performance
- Scores below 0.4: Poor performance

Recommendations:
----------------
"""
        
        # Add recommendations based on scores
        if scores['faithfulness'] < 0.7:
            report += "- Improve answer generation to reduce hallucinations\n"
        
        if scores['answer_relevancy'] < 0.7:
            report += "- Enhance prompt engineering for better answer relevance\n"
        
        if scores['context_precision'] < 0.7:
            report += "- Improve retrieval system to get more precise contexts\n"
        
        if scores['context_recall'] < 0.7:
            report += "- Increase top-k retrieval or improve chunking strategy\n"
        
        if scores['context_relevancy'] < 0.7:
            report += "- Optimize hybrid search weights or improve embeddings\n"
        
        if overall < 0.7:
            report += "- Consider fine-tuning the overall RAG pipeline\n"
        
        return report


async def main():
    """Main evaluation function"""
    try:
        # Initialize services
        vector_service = VectorService()
        await vector_service.initialize()
        
        chat_service = ChatService(vector_service)
        
        # Create evaluator
        evaluator = RAGEvaluator(chat_service, vector_service)
        
        # Run evaluation
        results = await evaluator.run_evaluation()
        
        # Save results
        filepath = evaluator.save_results(results)
        
        # Generate and print report
        report = evaluator.generate_report(results)
        print(report)
        
        # Save report
        report_path = filepath.replace('.json', '_report.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info("Evaluation completed successfully", 
                   results_file=filepath, 
                   report_file=report_path)
        
    except Exception as e:
        logger.error("Evaluation failed", error=str(e))
        raise
    finally:
        # Cleanup
        if 'vector_service' in locals():
            await vector_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
