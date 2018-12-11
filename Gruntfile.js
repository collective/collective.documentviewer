module.exports = function (grunt) {
    'use strict';
    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),
        // we could just concatenate everything, really
        // but we like to have it the complex way.
        // also, in this way we do not have to worry
        // about putting files in the correct order
        // (the dependency tree is walked by r.js)
        less: {
            dist: {
                options: {
                    plugins: [
                        new require('less-plugin-inline-urls'),
                    ],
                    paths: [],
                    strictMath: false,
                    sourceMap: true,
                    compress: true,
                    outputSourceFiles: true,
                    sourceMapURL: '++resource++dv.resources/stylesheets/viewer.css.map',
                    sourceMapFilename: 'collective/documentviewer/resources/stylesheets/viewer.css.map',
                    modifyVars: {
                        "isPlone": "false"
                    }
                },
                files: {
                    'collective/documentviewer/resources/stylesheets/viewer.css': 'collective/documentviewer/resources/stylesheets/viewer.less'
                }
            }
        },

        uglify: {
          dist: {
            options: {
              sourceMap: true,
              // beautify: true,
              // mangle: false,
              // compress: false
            },
            files: {
              'collective/documentviewer/resources/javascripts/build.min.js': [
                'collective/documentviewer/resources/assets/viewer.js',
                'collective/documentviewer/resources/assets/templates.js',
                'collective/documentviewer/resources/javascripts/viewer.js'
              ]
            }
          }
        },

        watch: {
            scripts: {
                files: [
                    'collective/documentviewer/resources/stylesheets/*.less',
                    'collective/documentviewer/resources/javascripts/viewer.js'
                ],
                tasks: ['less', 'uglify']
            }
        }
    });

    // grunt.loadTasks('tasks');
    grunt.loadNpmTasks('grunt-contrib-watch');
    grunt.loadNpmTasks('grunt-contrib-less');
    grunt.loadNpmTasks('grunt-contrib-copy');
    grunt.loadNpmTasks('grunt-sed');
    grunt.loadNpmTasks('grunt-contrib-uglify');
    grunt.registerTask('default', ['less', 'uglify', 'watch']);
    grunt.registerTask('build', ['less', 'uglify']);
};
