models = {}

def extract_models(module):
    # Get all classes in module with train and predict methods
    return {name: cls for name, cls in module.__dict__.items()
            if hasattr(cls, 'train') and hasattr(cls, 'predict')}
try:
    from .jax_models.regression_model import RegressionModel, HierarchicalRegressionModel
    from .jax_models.simple_ssm import SSM, SSMWithSigmoidEffect
    from .jax_models import regression_model, simple_ssm
    models = {**extract_models(regression_model), **extract_models(simple_ssm)}
    #models['RegressionModel'] = RegressionModel
    #models['HierarchicalRegressionModel'] = HierarchicalRegressionModel
    #models['SSM'] = SSM
    #models['SSMWithSigmoidEffect'] = SSMWithSigmoidEffect

except ImportError as e:
    print('Could not import RegressionModel')
    print(e)
