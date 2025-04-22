
from setuptools import setup, find_packages

setup(
    name='multimodelling',
    version='0.4.3',
    author= "Isaac",
    author_email= "isaacleis.garrote@usc.es",
    description = 'Library for Biorefinery modelling following the Multiscale Approach using BioSTEAM as a Framework',  
    long_description = open("README.md").read(),
    long_description_content_type= "text/markdown",
    url = "https://github.com/Biogroup-USC/multiscale-modelling-biorefinery-code.git", 
    packages = find_packages(),
    include_package_data = True  
)